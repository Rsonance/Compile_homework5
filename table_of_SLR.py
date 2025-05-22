#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：Compile_homework5 
@File    ：table_of_SLR.py
@IDE     ：PyCharm 
@Author  ：ZCTong
@Date    ：2025/5/22 14:31 
"""

import re
from collections import defaultdict, deque

# 文法定义
grammar_raw = """
P -> C Q
C -> ε | C D ;
D -> T d | T d [ i ] | T d ( N ) { C Q }
T -> int | void
N -> ε | N A ;
A -> T d | d [ ] | T d ( )
Q -> S | Q ; S
S -> d = E | if ( B ) S | if ( B ) S else S | while ( B ) S | return E | { Q } | d ( M )
B -> B ∧ B | B ∨ B | E r E | E
E -> d = E | i | d | d ( M ) | E + E | E * E | ( E )
M -> ε | M R ,
R -> E | d [ ] | d ( )
"""

# STEP 1: 将文法解析为产生式形式
def parse_grammar(grammar_str):
    productions = defaultdict(list)
    for line in grammar_str.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        head, bodies = line.split("->")
        head = head.strip()
        for body in bodies.strip().split('|'):
            symbols = body.strip().split()
            productions[head].append(symbols)
    return productions

# 增广文法
def augment_grammar(productions):
    start = list(productions.keys())[0]
    productions["S'"] = [[start]]
    return "S'", productions

# LR(0) 项目类
class Item:
    def __init__(self, lhs, rhs, dot_pos=0):
        self.lhs = lhs
        self.rhs = rhs
        self.dot = dot_pos

    def __eq__(self, other):
        return self.lhs == other.lhs and self.rhs == other.rhs and self.dot == other.dot

    def __hash__(self):
        return hash((self.lhs, tuple(self.rhs), self.dot))

    def __repr__(self):
        rhs = self.rhs.copy()
        rhs.insert(self.dot, '·')
        return f"{self.lhs} -> {' '.join(rhs)}"

# 构造闭包
def closure(items, productions):
    closure_set = set(items)
    changed = True
    while changed:
        changed = False
        new_items = set()
        for item in closure_set:
            if item.dot < len(item.rhs):
                sym = item.rhs[item.dot]
                if sym in productions:
                    for prod in productions[sym]:
                        new_item = Item(sym, prod, 0)
                        if new_item not in closure_set:
                            new_items.add(new_item)
        if new_items:
            closure_set.update(new_items)
            changed = True
    return frozenset(closure_set)

# GOTO 函数
def goto(items, symbol, productions):
    moved_items = set()
    for item in items:
        if item.dot < len(item.rhs) and item.rhs[item.dot] == symbol:
            moved_items.add(Item(item.lhs, item.rhs, item.dot + 1))
    return closure(moved_items, productions)

# 构造 LR(0) 项目集族
def build_states(start_symbol, productions):
    initial = closure([Item(start_symbol, productions[start_symbol][0], 0)], productions)
    states = [initial]
    transitions = {}
    symbols = set(s for prods in productions.values() for prod in prods for s in prod)

    queue = deque([initial])
    while queue:
        current = queue.popleft()
        for symbol in symbols:
            target = goto(current, symbol, productions)
            if target and target not in states:
                states.append(target)
                queue.append(target)
            if target:
                transitions[(states.index(current), symbol)] = states.index(target)
    return states, transitions

# 计算 FOLLOW 集
def compute_follow(productions, start_symbol):
    follow = defaultdict(set)
    follow[start_symbol].add('$')
    changed = True
    while changed:
        changed = False
        for lhs, rhs_list in productions.items():
            for rhs in rhs_list:
                for i, sym in enumerate(rhs):
                    if sym in productions:
                        trailer = rhs[i+1:]
                        if trailer:
                            first_of_trailer = set()
                            for t in trailer:
                                if t not in productions:
                                    first_of_trailer.add(t)
                                    break
                                else:
                                    for prod in productions[t]:
                                        if prod[0] != 'ε':
                                            first_of_trailer.add(prod[0])
                                            break
                            if not first_of_trailer <= follow[sym]:
                                follow[sym].update(first_of_trailer)
                                changed = True
                        else:
                            if not follow[lhs] <= follow[sym]:
                                follow[sym].update(follow[lhs])
                                changed = True
    return follow

# 构造 SLR(1) 表格
def build_slr_table(states, transitions, productions, follow):
    ACTION = defaultdict(dict)
    GOTO = defaultdict(dict)
    state_map = {s: i for i, s in enumerate(states)}
    terminals = set()
    nonterminals = set(productions.keys())
    for lhs in productions:
        for rhs in productions[lhs]:
            for sym in rhs:
                if sym not in productions and sym != 'ε':
                    terminals.add(sym)

    for i, state in enumerate(states):
        for item in state:
            if item.dot < len(item.rhs):
                a = item.rhs[item.dot]
                if a in terminals:
                    j = transitions.get((i, a))
                    if j is not None:
                        ACTION[i][a] = f"s{j}"
                elif a in nonterminals:
                    j = transitions.get((i, a))
                    if j is not None:
                        GOTO[i][a] = j
            else:
                if item.lhs == "S'":
                    ACTION[i]['$'] = 'acc'
                else:
                    for a in follow[item.lhs]:
                        ACTION[i][a] = f"r{item.lhs}->{ ' '.join(item.rhs) }"

    return ACTION, GOTO

# 主程序
productions = parse_grammar(grammar_raw)
start_symbol, productions = augment_grammar(productions)
states, transitions = build_states(start_symbol, productions)
follow = compute_follow(productions, start_symbol)
action_table, goto_table = build_slr_table(states, transitions, productions, follow)

# 输出 ACTION 和 GOTO 表
print("=== ACTION Table ===")
for state in sorted(action_table.keys()):
    print(f"State {state}: {action_table[state]}")

print("\n=== GOTO Table ===")
for state in sorted(goto_table.keys()):
    print(f"State {state}: {goto_table[state]}")
