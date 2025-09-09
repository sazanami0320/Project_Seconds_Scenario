from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Footer, ContentSwitcher
from typing import Tuple, Any
from pathlib import Path
from time import sleep

from exception import SourcedException
from .scenario_select import ScenarioSelect
from .asset_match import AssetMatcher
from .alarm import Alarm
from .error import Error
from .utils import to_ast, to_ir

GUI_DIR = Path(__file__).resolve().parent


class MakeApp(App):

    BINDINGS = [('q', 'quit', '退出')]

    def __init__(self):
        super().__init__(css_path=GUI_DIR / 'style.tcss')
        self.suppress_level = 0
        self.poll_lock = False
        self.match_result = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(can_focus=False):
            with ContentSwitcher(initial='src-select', id='main-cs'):
                yield ScenarioSelect(id='src-select')
                yield AssetMatcher(id='asset-match')
                yield Alarm(id='alarm')
                yield Error(id='error')
        yield Footer()

    def set_content(self, content_id: str):
        cs = self.query_exactly_one('#main-cs')
        cs.current = content_id
        cs.visible_content.focus()
        if content_id == 'src-select':
            cs.disabled = False

    def alarm(self, msg: str):
        self.query_exactly_one(Alarm).content = msg
        self.set_content('alarm')
    
    def reset(self):
        self.set_content('src-select')

    def lock(self):
        self.poll_lock = True

    def is_locked(self):
        return self.poll_lock

    def get_match_result(self):
        return self.match_result
    
    @on(ScenarioSelect.ScenarioSelected)
    def on_src_selected(self, message: ScenarioSelect.ScenarioSelected):
        self.scenario_dir = message.scenario_dir
        self.suppress_level = message.suppress_level
        self.start_compile()

    @on(Error.FailMessage)
    def on_fail(self):
        # Reset to step one
        self.reset()

    @on(Error.RetryMessage)
    def on_retry(self):
        self.start_compile()

    @on(AssetMatcher.MatchFinish)
    def on_matched(self, msg: AssetMatcher.MatchFinish):
        self.match_result = msg.match_result
        self.poll_lock = False
    
    @work(exclusive=True, thread=True)
    def start_compile(self):
        # Startpoint. This resembles the main function in make.py.
        # With workers in textual we now have a full thread for working.
        # It's way too hard to fix all my previous serial codes into async-aware ones
        # so threading might be the best solution.
        self.call_from_thread(self.alarm, f"正在尝试编译{self.scenario_dir.stem}...")
        self.query_exactly_one(Error).scenario_dir = self.scenario_dir # This is not reactive
        status, (objs, titles) = self.wrapped_call(to_ast, self.scenario_dir)
        # Any fail would end this worker.
        if not status:
            return
        status, irs = self.wrapped_call(to_ir, self.scenario_dir.stem, objs, titles, self.suppress_level, self.ask_hook)
        # GUI is only used for asset mapping.
        # You can use CLI to generate KAG scripts.
        # (If you want it then you have to PR it)
        self.reset()
    
    # The functions below all runs in a different thread and should be taken care of as the result.
    def wrapped_call(self, func, *args, **kwargs) -> Tuple[bool, Any]:
        self.call_from_thread(self.query_exactly_one(Error).reset)
        try:
            ret = func(*args, **kwargs)
        except SourcedException as e:
            self.call_from_thread(self.query_exactly_one(Error).report_sourced_error, e)
            self.call_from_thread(self.set_content, 'error')
            return (False, None)
        return (True, ret)

    def ask_hook(self, name, hierarchy, ask_set):
        self.call_from_thread(self.query_exactly_one(AssetMatcher).start_match, name, ask_set, hierarchy)
        self.call_from_thread(self.set_content, 'asset-match')
        # Well, we have to poll somewhere if we do not use multithreading or async.
        # Yes, this is not reactive, but I'm worried about thread safety so
        self.call_from_thread(self.lock)
        while self.call_from_thread(self.is_locked):
            sleep(1)
        return self.call_from_thread(self.get_match_result)
