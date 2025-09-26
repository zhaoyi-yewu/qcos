from __future__ import annotations
import networkx as nx
from .base_node import CalibrationNode, State
from typing import Any
from collections import defaultdict
import matplotlib.pyplot as plt
import time
import logging
from copy import deepcopy
from apscheduler.schedulers.background import BackgroundScheduler


class Calibration():
    '''
    calibration class, which contains dag and update process
    参考《Physical qubit calibration on a directed acyclic graph》
    Args:
        qubit: which qubit this calibration corresponded to
        cal_node: calibration node list
    '''

    def __init__(self,
                 qubit: str | int,
                 cal_node: list[CalibrationNode] = [],
                 logger=logging.getLogger(__name__)
                 ) -> None:

        self._qibit = qubit
        self._cal_node = {}
        self.logger = logger
        for cal in cal_node:
            self.add_node(cal)

        self.scheduler = BackgroundScheduler()

    def add_node(self, cal_node: CalibrationNode) -> None:
        '''
        Add calibration node to this calibration
        '''

        if cal_node.name in self._cal_node:
            raise RuntimeError(f"{cal_node.name} is already in calibration processor")

        self._cal_node[cal_node.name] = cal_node

    def build_dg(self) -> None:
        '''
        Build dg from calibration node list
        '''

        self.dg = nx.DiGraph()
        for node in self._cal_node:
            self.dg.add_node(
                node,
                cal=self._cal_node[node]
            )

        for node in self._cal_node:
            for dep in self._cal_node[node].dependency:
                if dep.instance == None: continue  # raise RuntimeError(f"{dep.__name__} has no instance")
                dep = dep.instance
                if dep.name not in self._cal_node: raise RuntimeError(
                    f"{node}'s depend {dep.name} is not add to calibration processor")
                self.dg.add_edge(
                    node,
                    dep.name
                )

    def get_scc(self) -> Any:
        '''
        Find strongly connected component using tarjan algo
        '''

        low = defaultdict(int)
        dfn = defaultdict(int)
        num = 1
        stack = []
        scc = []

        def tarjan(node: str):

            if dfn[node] > 0: return

            nonlocal num
            dfn[node] = num
            low[node] = num
            stack.append(node)
            num += 1
            for nxt in self.dg.neighbors(node):
                if (dfn[nxt] == 0):
                    tarjan(nxt)
                    low[node] = min(low[node], low[nxt])
                elif nxt in stack:
                    low[node] = min(low[node], dfn[nxt])

            loop = []
            if low[node] == dfn[node]:
                while stack[-1] != node:
                    loop.append(stack[-1])
                    stack.pop(-1)
                loop.append(stack[-1])
                stack.pop(-1)
            if len(loop) > 1: scc.append(loop)

        for node in self.dg.nodes():
            tarjan(node)
        return scc

    def get_calibrate_sequence(self):
        """
        get all nodes' calibration sequence, which according to topological order
        """
        dg = deepcopy(self.dg)
        self.calibrate_sequence = [node for (node, d) in dg.out_degree() if d == 0]
        layer = self.calibrate_sequence.copy()
        while layer:
            for node in layer:
                dg.remove_node(node)
            layer = [node for (node, d) in dg.out_degree() if d == 0]
            self.calibrate_sequence += layer
        assert len(self.calibrate_sequence) == len(self.dg.nodes())

    def draw_topo(self):
        '''
        Draw the current directed graph
        '''

        pos = nx.spring_layout(self.dg)
        nx.draw(self.dg.reverse(), pos=pos, with_labels=True, alpha=0.5)
        plt.show()

    def check_state(self, node: str) -> bool:
        '''
        check current node's state, using recursion
        '''
        node = self.get_node_name(node)
        # self.logger.debug(f"{node}: check state")

        state = True
        for nxt in self.dg.neighbors(node):
            state &= self.check_state(nxt)
            if self.dg.nodes[nxt]['cal'].calib_time > self.dg.nodes[node]['cal'].check_time:
                return False

        if time.time() - self.dg.nodes[node]['cal'].check_time > self.dg.nodes[node]['cal'].time_threshold:
            state = False
        return state

    def check_data(self, node) -> State:
        '''
        check current node's state by check function
        '''
        node = self.get_node_name(node)
        self.logger.debug(f"{node}: check")
        return self.dg.nodes[node]['cal'].do_check()

    def diagnose(self, node) -> bool:
        '''
        top-down diagnose，which check current node's state and do calibrations or throw system error
        '''
        node = self.get_node_name(node)
        # self.logger.debug(f"{node}: diagnose")

        state = self.check_data(node)

        if state == State.in_spec: return False

        if state == State.bad:

            recalib = []
            for nxt in self.dg.neighbors(node):
                recalib.append(self.diagnose(nxt))

            if not any(recalib): raise RuntimeError("system error")

        self.logger.debug(f"{node}: calibrate")
        self.dg.nodes[node]['cal'].do_calibrate()
        return True

    def update(self, node) -> None:
        '''
        update process for this calibration
        '''
        node = self.get_node_name(node)
        state = self.check_state(node)

        if not state:
            self.diagnose(node)

    def recalibrate(self, node, t=None) -> None:
        '''
        all node after `node` do calibrate
        '''
        if t == None: t = time.time()
        node = self.get_node_name(node)
        for nxt in self.dg.neighbors(node):
            self.recalibrate(nxt, t)
        if self.dg.nodes[node]['cal'].calib_time < t:
            self.logger.debug(f"{node}: calibrate")
            self.dg.nodes[node]['cal'].do_calibrate()

    def calibrate_all(self):
        """
        all node do calibration
        """
        self.get_calibrate_sequence()
        for node in self.calibrate_sequence:
            self.logger.debug(f"{node}: calibrate")
            self.dg.nodes[node]['cal'].do_calibrate()

    def get_node_name(self, node) -> None:
        if isinstance(node, str): return node
        if isinstance(node, CalibrationNode): return node.name
        raise RuntimeError("please give node name or instance")

    def clear_job(self):
        self.scheduler.remove_all_jobs()

    def add_job(self, func: callable, interval=86400, id=None, kwargs={}):
        if id is None:
            id = f'{func.__name__}_{time.time()}'
        self.scheduler.add_job(func, 'interval', seconds=interval, id=id, kwargs=kwargs)

    def print_jobs(self):
        self.scheduler.print_jobs()

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown()
