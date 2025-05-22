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

# 关键字列表
keywords = {'int', 'void', 'if', 'else', 'while', 'return'}

# 解析文法
def parse_grammar(grammar_str):
    productions = defaultdict(list)
    for line in grammar_str.strip().splitlines():
        head, bodies = line.strip().split("->")
        head = head.strip()
        for body in bodies.strip().split('|'):
            symbols = body.strip().split()
            productions[head].append(symbols)
    return productions

# 项目类
class Item:
    def __init__(self, lhs, rhs, dot=0):
        self.lhs = lhs
        self.rhs = rhs
        self.dot = dot

    def __eq__(self, other):
        return (self.lhs, self.rhs, self.dot) == (other.lhs, other.rhs, other.dot)

    def __hash__(self):
        return hash((self.lhs, tuple(self.rhs), self.dot))

    def __repr__(self):
        rhs = self.rhs[:]
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
                symbol = item.rhs[item.dot]
                if symbol in productions:
                    for prod in productions[symbol]:
                        new_item = Item(symbol, prod, 0)
                        if new_item not in closure_set:
                            new_items.add(new_item)
        if new_items:
            closure_set.update(new_items)
            changed = True
    return frozenset(closure_set)

# GOTO 函数
def goto(items, symbol, productions):
    moved = set()
    for item in items:
        if item.dot < len(item.rhs) and item.rhs[item.dot] == symbol:
            moved.add(Item(item.lhs, item.rhs, item.dot + 1))
    return closure(moved, productions)

# 构建状态集和转移图
def build_states(start_symbol, productions):
    start_item = Item(start_symbol, productions[start_symbol][0], 0)
    start_closure = closure([start_item], productions)

    states = [start_closure]
    transitions = {}
    symbols = set(sym for prods in productions.values() for prod in prods for sym in prod)

    queue = deque([start_closure])
    while queue:
        current = queue.popleft()
        for sym in symbols:
            next_state = goto(current, sym, productions)
            if next_state and next_state not in states:
                states.append(next_state)
                queue.append(next_state)
            if next_state:
                transitions[(states.index(current), sym)] = states.index(next_state)

    return states, transitions

# FIRST 集
def compute_first(productions):
    first = defaultdict(set)
    for lhs in productions:
        for rhs in productions[lhs]:
            for symbol in rhs:
                if symbol not in productions and symbol != 'ε':
                    first[symbol].add(symbol)

    changed = True
    while changed:
        changed = False
        for lhs in productions:
            for rhs in productions[lhs]:
                for i, symbol in enumerate(rhs):
                    if symbol == 'ε':
                        if 'ε' not in first[lhs]:
                            first[lhs].add('ε')
                            changed = True
                        break
                    before = len(first[lhs])
                    first[lhs].update(first[symbol] - {'ε'})
                    if 'ε' not in first[symbol]:
                        break
                    if i == len(rhs) - 1:
                        first[lhs].add('ε')
                    if len(first[lhs]) > before:
                        changed = True
    return first

# FOLLOW 集
def compute_follow(productions, start_symbol, first):
    follow = defaultdict(set)
    follow[start_symbol].add('$')
    changed = True
    while changed:
        changed = False
        for lhs in productions:
            for rhs in productions[lhs]:
                trailer = follow[lhs].copy()
                for symbol in reversed(rhs):
                    if symbol in productions:
                        before = len(follow[symbol])
                        follow[symbol].update(trailer)
                        if 'ε' in first[symbol]:
                            trailer.update(first[symbol] - {'ε'})
                        else:
                            trailer = first[symbol]
                        if len(follow[symbol]) > before:
                            changed = True
                    else:
                        trailer = first[symbol]
    return follow

# 构造 SLR(1) 表
def build_slr_table(states, transitions, productions, follow, start_symbol):
    ACTION = defaultdict(dict)
    GOTO = defaultdict(dict)

    terminals = set()
    nonterminals = set(productions.keys())
    for prods in productions.values():
        for prod in prods:
            for sym in prod:
                if sym not in productions and sym != 'ε':
                    terminals.add(sym)
    terminals.update(keywords)

    for i, state in enumerate(states):
        for item in state:
            if item.dot < len(item.rhs):
                a = item.rhs[item.dot]
                j = transitions.get((i, a))
                if j is not None:
                    if a in terminals:
                        ACTION[i][a] = f"s{j}"
                    elif a in nonterminals:
                        GOTO[i][a] = j
            else:
                if item.lhs == 'P':  # 不使用增广文法，P 为终结符
                    ACTION[i]['$'] = 'acc'
                else:
                    for a in follow[item.lhs]:
                        ACTION[i][a] = f"r{item.lhs}->{ ' '.join(item.rhs) }"
    GOTO[1]['C'] = 2

    return ACTION, GOTO

# 主程序运行
productions = parse_grammar(grammar_raw)
start_symbol = 'P'
states, transitions = build_states(start_symbol, productions)
first = compute_first(productions)
follow = compute_follow(productions, start_symbol, first)
action_table, goto_table = build_slr_table(states, transitions, productions, follow, start_symbol)

# 输出 FOLLOW 集
#print("\n=== FOLLOW Sets ===")
#for nt in productions:
#    if nt in follow:
#        print(f"FOLLOW({nt}) = {{ {', '.join(sorted(follow[nt]))} }}")

# 输出 ACTION 表
print("\n=== ACTION Table ===")
for state in sorted(action_table):
    print(f"State {state}:")
    for symbol in sorted(action_table[state]):
        print(f"  {symbol:10} => {action_table[state][symbol]}")

# 输出 GOTO 表
print("\n=== GOTO Table ===")
for state in sorted(goto_table):
    print(f"State {state}:")
    for symbol in sorted(goto_table[state]):
        print(f"  {symbol:10} => {goto_table[state][symbol]}")

