#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
修复后的SLR语法分析器 - 解决语法错误问题
主要修复：
1. 统一文法定义与sentences.txt保持一致
2. 修复状态转移和ACTION表构建问题
3. 解决函数体结束时的归约问题
"""

import re
from typing import List, Tuple, Dict, Any, Optional
from collections import defaultdict, deque


class TokenMapper:
    """处理词法token到语法符号的映射"""
    
    @staticmethod
    def map_token_to_symbol(token_type: str, token_val: str) -> str:
        """将词法token映射为语法分析用的终结符"""
        token_map = {
            "ID": "d",
            "NUMBER": "i",
            "LPA": "(",
            "RPA": ")",
            "LBR": "[",
            "RBR": "]",
            "LCU": "{",
            "RCU": "}",
            "SCO": ";",
            "ASG": "=",
            "ADD": "+",
            "MUL": "*",
            "COM": ",",
            "AND": "∧",
            "OR": "∨",
            "REL": "r"
        }
        
        if token_type in token_map:
            return token_map[token_type]
        elif token_type == "KEY":
            return token_val  # 关键字直接使用值
        else:
            return token_val


class Grammar:
    """处理文法解析和FIRST/FOLLOW集计算"""
    
    def __init__(self):
        self.productions = defaultdict(list)
        self.productions_list = []
        self.first = {}
        self.follow = {}
        self.initialize_grammar()
    
    def initialize_grammar(self):
        """根据sentences.txt初始化文法，修复语法问题"""
        # 扩展文法，添加开始产生式
        grammar_rules = [
            ("P'", ["P"]),  # 0: 扩展开始产生式
            ("P", ["C", "Q"]),  # 1
            ("C", ["ε"]),  # 2
            ("C", ["C", "D", ";"]),  # 3
            ("D", ["T", "d"]),  # 4
            ("D", ["T", "d", "[", "i", "]"]),  # 5
            ("D", ["T", "d", "(", "N", ")", "{", "C", "Q", "}"]),  # 6
            ("T", ["int"]),  # 7
            ("T", ["void"]),  # 8
            ("N", ["ε"]),  # 9
            ("N", ["N", "A", ";"]),  # 10
            ("A", ["T", "d"]),  # 11
            ("A", ["d", "[", "]"]),  # 12
            ("A", ["T", "d", "(", ")"]),  # 13
            ("Q", ["S"]),  # 14
            ("Q", ["Q", ";", "S"]),  # 15
            ("S", ["d", "=", "E"]),  # 16
            ("S", ["if", "(", "B", ")", "S"]),  # 17
            ("S", ["if", "(", "B", ")", "S", "else", "S"]),  # 18
            ("S", ["while", "(", "B", ")", "S"]),  # 19
            ("S", ["return", "E"]),  # 20
            ("S", ["{", "Q", "}"]),  # 21
            ("S", ["d", "(", "M", ")"]),  # 22
            ("B", ["B", "∧", "B"]),  # 23
            ("B", ["B", "∨", "B"]),  # 24
            ("B", ["E", "r", "E"]),  # 25
            ("B", ["E"]),  # 26
            ("E", ["d", "=", "E"]),  # 27
            ("E", ["i"]),  # 28
            ("E", ["d"]),  # 29
            ("E", ["d", "(", "M", ")"]),  # 30
            ("E", ["E", "+", "E"]),  # 31
            ("E", ["E", "*", "E"]),  # 32
            ("E", ["(", "E", ")"]),  # 33
            ("M", ["ε"]),  # 34
            ("M", ["M", "R", ","]),  # 35
            ("R", ["E"]),  # 36
            ("R", ["d", "[", "]"]),  # 37
            ("R", ["d", "(", ")"]),  # 38
        ]
        
        for lhs, rhs in grammar_rules:
            self.productions[lhs].append(rhs)
            self.productions_list.append((lhs, rhs))
    
    def compute_first(self):
        """计算FIRST集"""
        self.first = defaultdict(set)
        
        # 终结符的FIRST集就是自身
        terminals = {'int', 'void', 'if', 'else', 'while', 'return',
                     '(', ')', '[', ']', '{', '}', ';', '=', '+', '*',
                     '∧', '∨', 'r', ',', 'd', 'i', '$', 'ε'}
        
        for t in terminals:
            self.first[t].add(t)
        
        # 迭代计算非终结符的FIRST集
        changed = True
        while changed:
            changed = False
            for lhs in self.productions:
                old_size = len(self.first[lhs])
                
                for rhs in self.productions[lhs]:
                    if rhs == ['ε']:
                        self.first[lhs].add('ε')
                    else:
                        # 处理右部的每个符号
                        all_have_epsilon = True
                        for symbol in rhs:
                            # 添加FIRST(symbol) - {ε}
                            self.first[lhs].update(self.first[symbol] - {'ε'})
                            
                            # 如果symbol不包含ε，停止
                            if 'ε' not in self.first[symbol]:
                                all_have_epsilon = False
                                break
                        
                        # 如果所有符号都包含ε，则添加ε
                        if all_have_epsilon:
                            self.first[lhs].add('ε')
                
                if len(self.first[lhs]) > old_size:
                    changed = True
    
    def compute_follow(self, start_symbol):
        """计算FOLLOW集"""
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
                            
                            # 获取β (symbol后面的符号)
                            beta = rhs[i + 1:]
                            
                            if not beta:
                                # β为空，添加FOLLOW(A)
                                self.follow[symbol].update(self.follow[lhs])
                            else:
                                # 计算FIRST(β)
                                first_beta = set()
                                all_epsilon = True
                                
                                for b_sym in beta:
                                    first_beta.update(self.first[b_sym] - {'ε'})
                                    if 'ε' not in self.first[b_sym]:
                                        all_epsilon = False
                                        break
                                
                                self.follow[symbol].update(first_beta)
                                
                                # 如果FIRST(β)包含ε，添加FOLLOW(A)
                                if all_epsilon:
                                    self.follow[symbol].update(self.follow[lhs])
                            
                            if len(self.follow[symbol]) > old_size:
                                changed = True
        
        # 确保正确的FOLLOW集
        # Q的FOLLOW集应该包含 } 因为在函数定义中
        self.follow['Q'].add('}')
        # S的FOLLOW集应该包含 } 和 ;
        self.follow['S'].update({'}', ';', 'else'})


class Item:
    """LR(0)项"""
    
    def __init__(self, lhs, rhs, dot=0):
        self.lhs = lhs
        self.rhs = rhs[:]
        self.dot = dot
    
    def __eq__(self, other):
        return (self.lhs, tuple(self.rhs), self.dot) == (other.lhs, tuple(other.rhs), other.dot)
    
    def __hash__(self):
        return hash((self.lhs, tuple(self.rhs), self.dot))
    
    def __repr__(self):
        rhs_with_dot = self.rhs[:]
        rhs_with_dot.insert(self.dot, '·')
        return f"{self.lhs} -> {' '.join(rhs_with_dot)}"
    
    def is_complete(self):
        """检查项是否完成"""
        return self.dot >= len(self.rhs) or (len(self.rhs) == 1 and self.rhs[0] == 'ε')
    
    def next_symbol(self):
        """获取点后的符号"""
        if self.is_complete() or self.rhs == ['ε']:
            return None
        return self.rhs[self.dot]


class SLRParser:
    """SLR(1)解析器"""
    
    def __init__(self, grammar, start_symbol):
        self.grammar = grammar
        self.start_symbol = start_symbol
        self.states = []
        self.transitions = {}
        self.action_table = {}
        self.goto_table = {}
        self.build_parser()
    
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
        """计算GOTO(I, X)"""
        moved_items = set()
        
        for item in items:
            if item.next_symbol() == symbol:
                new_item = Item(item.lhs, item.rhs, item.dot + 1)
                moved_items.add(new_item)
        
        if moved_items:
            return self.closure(moved_items)
        else:
            return frozenset()
    
    def build_states(self):
        """构建状态集合"""
        # 初始状态
        start_item = Item(self.start_symbol, self.grammar.productions[self.start_symbol][0], 0)
        start_state = self.closure([start_item])
        
        self.states = [start_state]
        
        # 收集所有符号
        all_symbols = set()
        for prods in self.grammar.productions.values():
            for prod in prods:
                for sym in prod:
                    if sym != 'ε':
                        all_symbols.add(sym)
        
        # 构建状态转移
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
    
    def build_tables(self):
        """构建ACTION和GOTO表"""
        terminals = {'int', 'void', 'if', 'else', 'while', 'return',
                     '(', ')', '[', ']', '{', '}', ';', '=', '+', '*',
                     '∧', '∨', 'r', ',', 'd', 'i', '$'}
        nonterminals = set(self.grammar.productions.keys())
        
        # 初始化表
        for i in range(len(self.states)):
            self.action_table[i] = {}
            self.goto_table[i] = {}
        
        for state_idx, state in enumerate(self.states):
            for item in state:
                if not item.is_complete():
                    # 移进动作
                    next_sym = item.next_symbol()
                    if next_sym and (state_idx, next_sym) in self.transitions:
                        next_state = self.transitions[(state_idx, next_sym)]
                        
                        if next_sym in terminals:
                            if next_sym in self.action_table[state_idx]:
                                # 检查冲突
                                existing = self.action_table[state_idx][next_sym]
                                if not existing.startswith('s'):
                                    print(
                                        f"移进/归约冲突在状态{state_idx}, 符号'{next_sym}': {existing} vs s{next_state}")
                            else:
                                self.action_table[state_idx][next_sym] = f"s{next_state}"
                        elif next_sym in nonterminals:
                            self.goto_table[state_idx][next_sym] = next_state
                else:
                    # 归约动作
                    if (item.lhs == self.start_symbol and
                            item.rhs == self.grammar.productions[self.start_symbol][0]):
                        self.action_table[state_idx]['$'] = 'acc'
                    else:
                        # 查找产生式索引
                        prod = (item.lhs, item.rhs)
                        try:
                            prod_idx = self.grammar.productions_list.index(prod)
                            
                            # 为FOLLOW(item.lhs)中的符号添加归约动作
                            for follow_sym in self.grammar.follow[item.lhs]:
                                if follow_sym in self.action_table[state_idx]:
                                    existing = self.action_table[state_idx][follow_sym]
                                    if existing != f"r{prod_idx}":
                                        print(
                                            f"归约/归约冲突在状态{state_idx}, 符号'{follow_sym}': {existing} vs r{prod_idx}")
                                else:
                                    self.action_table[state_idx][follow_sym] = f"r{prod_idx}"
                        except ValueError:
                            print(f"警告：找不到产生式 {prod}")
    
    def build_parser(self):
        """构建解析器"""
        self.grammar.compute_first()
        self.grammar.compute_follow(self.start_symbol)
        self.build_states()
        self.build_tables()


class SLRParserEngine:
    """SLR语法分析引擎"""
    
    def __init__(self):
        self.grammar = Grammar()
        self.parser = SLRParser(self.grammar, "P'")
        self.debug = True
    
    def parse_tokens(self, token_lines: List[str]) -> List[Tuple[str, str]]:
        """解析token文件"""
        tokens = []
        for line in token_lines:
            line = line.strip()
            if not line:
                continue
            
            # 改进的正则表达式，处理特殊字符
            if line.startswith('(') and line.endswith(')'):
                # 移除外层括号
                content = line[1:-1]
                # 找到第一个逗号分割点
                comma_pos = content.find(', ')
                if comma_pos != -1:
                    token_type = content[:comma_pos].strip()
                    token_val = content[comma_pos + 2:].strip()
                    tokens.append((token_type, token_val))
                    continue
            
            print(f"警告：无法解析token行: {line}")
        
        # 只添加一个结束符
        if not tokens or tokens[-1] != ("$", "$"):
            tokens.append(("$", "$"))
        return tokens
    
    def parse(self, tokens: List[Tuple[str, str]]) -> bool:
        """执行语法分析"""
        if self.debug:
            print("\n=== 映射后的终结符序列 ===")
            for i, (token_type, token_val) in enumerate(tokens):
                mapped = TokenMapper.map_token_to_symbol(token_type, token_val)
                print(f"{i:2d}: ({token_type:8}, {token_val:10}) -> '{mapped}'")
        
        # 初始化分析栈
        state_stack = [0]
        symbol_stack = []
        value_stack = []
        
        token_index = 0
        step = 0
        
        if self.debug:
            print(f"\n=== 语法分析过程 ===")
            print(f"{'步骤':<4} {'状态栈':<20} {'符号栈':<25} {'输入':<15} {'动作':<15}")
            print("-" * 85)
        
        while token_index < len(tokens):
            current_state = state_stack[-1]
            token_type, token_val = tokens[token_index]
            current_symbol = TokenMapper.map_token_to_symbol(token_type, token_val)
            
            # 获取动作
            action = self.parser.action_table[current_state].get(current_symbol)
            
            if self.debug:
                state_str = str(state_stack)
                symbol_str = str(symbol_stack)
                input_str = f"{current_symbol}({token_val})"
                action_str = action if action else "ERROR"
                
                print(f"{step:<4} {state_str:<20} {symbol_str:<25} {input_str:<15} {action_str:<15}")
                step += 1
            
            if action is None:
                print(f"\n语法错误：在状态 {current_state} 遇到符号 '{current_symbol}' 时无对应动作")
                print(f"当前状态可用动作：{list(self.parser.action_table[current_state].keys())}")
                return False
            
            if action.startswith("s"):  # 移进
                next_state = int(action[1:])
                state_stack.append(next_state)
                symbol_stack.append(current_symbol)
                value_stack.append(token_val)
                token_index += 1
            
            elif action.startswith("r"):  # 归约
                prod_idx = int(action[1:])
                lhs, rhs = self.grammar.productions_list[prod_idx]
                
                if self.debug:
                    print(f"    规约使用产生式 {prod_idx}: {lhs} -> {' '.join(rhs)}")
                
                # 弹出符号
                pop_count = 0 if rhs == ['ε'] else len(rhs)
                
                if pop_count > 0:
                    del state_stack[-pop_count:]
                    del symbol_stack[-pop_count:]
                    del value_stack[-pop_count:]
                
                # 压入左部符号
                symbol_stack.append(lhs)
                value_stack.append("")
                
                # GOTO转移
                current_state = state_stack[-1]
                goto_state = self.parser.goto_table[current_state].get(lhs)
                
                if goto_state is None:
                    print(f"GOTO错误：在状态 {current_state} 找不到符号 '{lhs}' 的转移")
                    print(f"可用GOTO: {list(self.parser.goto_table[current_state].keys())}")
                    return False
                
                state_stack.append(goto_state)
            
            elif action == "acc":  # 接受
                if self.debug:
                    print("\n=== 分析成功！ ===")
                return True
            
            else:
                print(f"未知动作：{action}")
                return False
        
        return False


def main():
    """主函数"""
    print("=== 修复后的SLR(1)语法分析器 ===")
    
    try:
        # 读取token文件
        with open("output.txt", "r", encoding="utf-8") as f:
            token_lines = f.readlines()
        
        # 创建解析器
        engine = SLRParserEngine()
        
        # 解析tokens
        tokens = engine.parse_tokens(token_lines)
        
        print("=== 开始SLR语法分析 ===")
        
        # 执行语法分析
        success = engine.parse(tokens)
        
        if success:
            print("\n语法分析成功！程序符合语法规范。")
        else:
            print("\n语法分析失败！程序存在语法错误。")
    
    except FileNotFoundError:
        print("错误：找不到文件 'output.txt'")
    except Exception as e:
        print(f"运行时出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("HELLO")
    main()