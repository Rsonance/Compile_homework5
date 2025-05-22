#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：Compile_homework5
@File    ：table_of_SLR.py
@IDE     ：PyCharm
@Author  ：ZCTong
@Date    ：2025/5/22 14:31
@Description: 构建 SLR(1) 解析表，采用面向对象设计。包括文法解析、项集管理、FIRST/FOLLOW 集计算和 ACTION/GOTO 表生成。
              修复了表访问问题并提高了健壮性。
"""

from collections import defaultdict, deque


class Grammar:
    """处理文法解析和 FIRST/FOLLOW 集计算"""
    
    def __init__(self, grammar_str, keywords, special_symbols):
        self.keywords = keywords  # 关键字集合
        self.special_symbols = special_symbols  # 特殊符号集合
        self.productions = defaultdict(list)  # 产生式字典
        self.productions_list = []  # 产生式列表
        self.parse_grammar(grammar_str)  # 解析文法
        self.first = {}  # FIRST 集
        self.follow = {}  # FOLLOW 集
    
    def parse_grammar(self, grammar_str):
        """将文法字符串解析为产生式字典和列表"""
        for line in grammar_str.strip().splitlines():
            if not line.strip():
                continue
            head, bodies = line.strip().split(" -> ")
            head = head.strip()
            for body in bodies.strip().split(" | "):
                symbols = body.strip().split() if body.strip() != "ε" else ["ε"]
                self.productions[head].append(symbols)
                self.productions_list.append((head, symbols))
    
    def compute_first(self):
        """计算所有符号的 FIRST 集"""
        self.first = defaultdict(set)
        
        # 为终结符初始化 FIRST 集
        for sym in self.keywords | self.special_symbols:
            self.first[sym].add(sym)
        self.first['ε'].add('ε')
        
        # 迭代计算非终结符的 FIRST 集
        changed = True
        while changed:
            changed = False
            for lhs in self.productions:
                old_size = len(self.first[lhs])
                
                for rhs in self.productions[lhs]:
                    if rhs == ['ε']:
                        self.first[lhs].add('ε')
                    else:
                        # 处理右部每个符号
                        all_nullable = True
                        for symbol in rhs:
                            # 将 FIRST(symbol) - {ε} 添加到 FIRST(lhs)
                            self.first[lhs].update(self.first[symbol] - {'ε'})
                            
                            # 如果符号不包含 ε，停止
                            if 'ε' not in self.first[symbol]:
                                all_nullable = False
                                break
                        
                        # 如果右部所有符号都可空，添加 ε
                        if all_nullable:
                            self.first[lhs].add('ε')
                
                if len(self.first[lhs]) > old_size:
                    changed = True
        
        return dict(self.first)
    
    def compute_follow(self, start_symbol):
        """计算所有非终结符的 FOLLOW 集"""
        self.follow = defaultdict(set)
        self.follow[start_symbol].add('$')
        
        changed = True
        while changed:
            changed = False
            
            for lhs in self.productions:
                for rhs in self.productions[lhs]:
                    for i, symbol in enumerate(rhs):
                        if symbol in self.productions:  # 非终结符
                            old_size = len(self.follow[symbol])
                            
                            # 获取符号后的子序列
                            beta = rhs[i + 1:]
                            
                            if not beta:
                                self.follow[symbol].update(self.follow[lhs])
                            else:
                                first_beta = set()
                                all_nullable = True
                                
                                for b_symbol in beta:
                                    first_beta.update(self.first[b_symbol] - {'ε'})
                                    if 'ε' not in self.first[b_symbol]:
                                        all_nullable = False
                                        break
                                
                                self.follow[symbol].update(first_beta)
                                if all_nullable:
                                    self.follow[symbol].update(self.follow[lhs])
                            
                            if len(self.follow[symbol]) > old_size:
                                changed = True
        
        # 确保 N 的 FOLLOW 集包含 )，Q 的 FOLLOW 集包含 }
        if ')' not in self.follow['N']:
            self.follow['N'].add(')')
        if '}' not in self.follow['Q']:
            self.follow['Q'].add('}')
        
        return dict(self.follow)
    
    def print_sets(self):
        """打印 FIRST 和 FOLLOW 集以供调试"""
        print("\n=== FIRST 集 ===")
        for symbol in sorted(self.first):
            print(f"FIRST({symbol}) = {{ {', '.join(sorted(self.first[symbol]))} }}")
        
        print("\n=== FOLLOW 集 ===")
        for symbol in sorted(self.follow):
            if symbol in self.productions:  # 仅打印非终结符
                print(f"FOLLOW({symbol}) = {{ {', '.join(sorted(self.follow[symbol]))} }}")


class Item:
    """表示一个 LR(0) 项（例如 A -> α·β）"""
    
    def __init__(self, lhs, rhs, dot=0):
        self.lhs = lhs  # 产生式左部
        self.rhs = rhs[:]  # 右部副本，避免修改
        self.dot = dot  # 点的位置
    
    def __eq__(self, other):
        return (self.lhs, tuple(self.rhs), self.dot) == (other.lhs, tuple(other.rhs), other.dot)
    
    def __hash__(self):
        return hash((self.lhs, tuple(self.rhs), self.dot))
    
    def __repr__(self):
        rhs_with_dot = self.rhs[:]
        rhs_with_dot.insert(self.dot, '·')
        return f"{self.lhs} -> {' '.join(rhs_with_dot)}"
    
    def is_complete(self):
        """检查项是否完成（点在末尾）"""
        return self.dot >= len(self.rhs) or (len(self.rhs) == 1 and self.rhs[0] == 'ε')
    
    def next_symbol(self):
        """获取点后的符号，若已完成则返回 None"""
        if self.is_complete() or self.rhs == ['ε']:
            return None
        return self.rhs[self.dot]


class SLRParser:
    """管理 SLR(1) 解析器的构建，包括状态集和 ACTION/GOTO 表"""
    
    def __init__(self, grammar, start_symbol):
        self.grammar = grammar  # 文法对象
        self.start_symbol = start_symbol  # 开始符号
        self.states = []  # 状态集
        self.transitions = {}  # 转移表
        self.action_table = {}  # ACTION 表
        self.goto_table = {}  # GOTO 表
        self.build_states()  # 构建状态集
    
    def closure(self, items):
        """计算项集的闭包"""
        closure_set = set(items)
        changed = True
        
        while changed:
            changed = False
            new_items = set()
            
            for item in closure_set:
                next_sym = item.next_symbol()
                if next_sym and next_sym in self.grammar.productions:
                    # 为该非终结符添加所有产生式
                    for prod in self.grammar.productions[next_sym]:
                        new_item = Item(next_sym, prod, 0)
                        if new_item not in closure_set:
                            new_items.add(new_item)
            
            if new_items:
                closure_set.update(new_items)
                changed = True
        
        return frozenset(closure_set)
    
    def goto(self, items, symbol):
        """计算 GOTO(I, X) 对于状态 I 和符号 X"""
        moved_items = set()
        
        for item in items:
            next_sym = item.next_symbol()
            if next_sym == symbol:
                new_item = Item(item.lhs, item.rhs, item.dot + 1)
                moved_items.add(new_item)
        
        if moved_items:
            return self.closure(moved_items)
        else:
            return frozenset()
    
    def build_states(self):
        """构建 LR(0) 项集的规范集"""
        # 创建初始状态
        if self.start_symbol not in self.grammar.productions:
            raise ValueError(f"开始符号 {self.start_symbol} 未在文法中找到")
        
        start_prod = self.grammar.productions[self.start_symbol][0]
        start_item = Item(self.start_symbol, start_prod, 0)
        start_state = self.closure([start_item])
        
        self.states = [start_state]
        self.transitions = {}
        
        # 收集所有文法符号
        all_symbols = set()
        for prods in self.grammar.productions.values():
            for prod in prods:
                for sym in prod:
                    if sym != 'ε':
                        all_symbols.add(sym)
        all_symbols.update(self.grammar.keywords)
        all_symbols.update(self.grammar.special_symbols)
        
        # 使用队列构建状态
        queue = deque([0])
        
        while queue:
            current_idx = queue.popleft()
            current_state = self.states[current_idx]
            
            for symbol in all_symbols:
                next_state = self.goto(current_state, symbol)
                
                if next_state:
                    try:
                        next_idx = self.states.index(next_state)
                    except ValueError:
                        next_idx = len(self.states)
                        self.states.append(next_state)
                        queue.append(next_idx)
                    
                    self.transitions[(current_idx, symbol)] = next_idx
    
    def build_slr_table(self):
        """构建 SLR(1) 的 ACTION 和 GOTO 表"""
        terminals = self.grammar.keywords | self.grammar.special_symbols | {'$'}
        nonterminals = set(self.grammar.productions.keys())
        
        # 为每个状态初始化空字典
        for i in range(len(self.states)):
            self.action_table[i] = {}
            self.goto_table[i] = {}
        
        for state_idx, state in enumerate(self.states):
            for item in state:
                if not item.is_complete():
                    # 移进行动
                    next_sym = item.next_symbol()
                    if next_sym and (state_idx, next_sym) in self.transitions:
                        next_state = self.transitions[(state_idx, next_sym)]
                        
                        if next_sym in terminals:
                            # 移进行动
                            if next_sym in self.action_table[state_idx]:
                                print(f"警告：状态 {state_idx} 在符号 '{next_sym}' 上存在移进/归约冲突")
                            else:
                                self.action_table[state_idx][next_sym] = f"s{next_state}"
                        elif next_sym in nonterminals:
                            # GOTO 动作
                            self.goto_table[state_idx][next_sym] = next_state
                else:
                    # 归约动作
                    prod = (item.lhs, item.rhs)
                    
                    # 检查接受动作
                    if (item.lhs == self.start_symbol and
                            len(self.grammar.productions[self.start_symbol]) > 0 and
                            item.rhs == self.grammar.productions[self.start_symbol][0]):
                        self.action_table[state_idx]['$'] = 'acc'
                    else:
                        # 查找产生式索引
                        try:
                            prod_idx = self.grammar.productions_list.index(prod)
                            
                            # 为 FOLLOW(item.lhs) 中的所有符号添加归约动作
                            for follow_sym in self.grammar.follow[item.lhs]:
                                if follow_sym in self.action_table[state_idx]:
                                    current_action = self.action_table[state_idx][follow_sym]
                                    print(f"警告：状态 {state_idx} 在符号 '{follow_sym}' 上存在冲突："
                                          f"当前 {current_action}，新 r{prod_idx}")
                                else:
                                    self.action_table[state_idx][follow_sym] = f"r{prod_idx}"
                        
                        except ValueError:
                            print(f"错误：产生式 {prod} 未在产生式列表中找到")
    
    def print_tables(self):
        """打印状态项集、转移表、ACTION 表和 GOTO 表"""
        print("\n=== 状态项集 ===")
        for i, state in enumerate(self.states):
            print(f"状态 {i}:")
            for item in sorted(state, key=str):
                print(f"  {item}")
        
        print("\n=== 转移表 ===")
        if self.transitions:
            for (state, symbol), next_state in sorted(self.transitions.items()):
                print(f"状态 {state:2d} 在符号 '{symbol:10}' 上 => 状态 {next_state}")
        else:
            print("未找到转移")
        
        print("\n=== ACTION 表 ===")
        for state_idx in range(len(self.states)):
            print(f"状态 {state_idx}:")
            if self.action_table[state_idx]:
                for symbol in sorted(self.action_table[state_idx]):
                    action = self.action_table[state_idx][symbol]
                    print(f"  {symbol:10} => {action}")
            else:
                print("  <空>")
        
        print("\n=== GOTO 表 ===")
        for state_idx in range(len(self.states)):
            print(f"状态 {state_idx}:")
            if self.goto_table[state_idx]:
                for symbol in sorted(self.goto_table[state_idx]):
                    goto_state = self.goto_table[state_idx][symbol]
                    print(f"  {symbol:10} => {goto_state}")
            else:
                print("  <空>")
        
        print("\n=== 产生式（带索引） ===")
        for i, (lhs, rhs) in enumerate(self.grammar.productions_list):
            print(f"{i:2d}: {lhs} -> {' '.join(rhs)}")


# 文法定义（增广文法）
grammar_raw = """
P' -> P
P -> C Q
C -> ε | C D ;
D -> T d | T d [ i ] | T d ( N ) { C Q }
T -> int | void
N -> ε | N A ;
A -> T d | d [ ] | T d ( )
Q -> S | Q ; S
S -> d = E | if ( B ) S | if ( B ) S else S | while ( B ) S | return E | { Q } | d ( M )
B -> B ∧ T | B ∨ T | T
T -> T r F | F
F -> F + G | G
G -> G * H | H
H -> i | d | d ( M ) | ( E )
M -> ε | M R ,
R -> E | d [ ] | d ( )
"""

# 关键字和特殊符号
keywords = {'int', 'void', 'if', 'else', 'while', 'return'}
special_symbols = {'(', ')', '[', ']', '{', '}', ';', '=', '+', '*', '∧', '∨', 'r', ',', '$', 'd', 'i'}

# 全局变量，保持向后兼容
grammar_instance = None
parser_instance = None
productions = None
action_table = None
goto_table = None


def initialize_parser():
    """初始化解析器并导出表"""
    global grammar_instance, parser_instance, productions, action_table, goto_table
    
    # 初始化文法
    grammar_instance = Grammar(grammar_raw, keywords, special_symbols)
    
    # 计算 FIRST 和 FOLLOW 集
    grammar_instance.compute_first()
    grammar_instance.compute_follow("P'")
    
    # 创建 SLR 解析器
    parser_instance = SLRParser(grammar_instance, "P'")
    parser_instance.build_slr_table()
    
    # 导出以保持兼容性
    productions = grammar_instance.productions_list
    action_table = parser_instance.action_table
    goto_table = parser_instance.goto_table
    
    return grammar_instance, parser_instance


if __name__ == '__main__':
    grammar_instance, parser_instance = initialize_parser()
    
    # 打印调试用的集
    grammar_instance.print_sets()
    
    # 打印表
    parser_instance.print_tables()
