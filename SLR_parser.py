#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import re
from typing import List, Tuple, Dict, Any, Optional
from collections import defaultdict, deque
import uuid


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
            "REL": "r",
            "QST": "?",  # Question mark for ternary
            "COL": ":"  # Colon for ternary
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
        """根据sentences.txt初始化文法，修复语法问题，并添加三元运算符"""
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
            ("E", ["E", "?", "E", ":", "E"]),  # 34: 三元运算符
            ("M", ["ε"]),  # 35
            ("M", ["M", "R", ","]),  # 36
            ("R", ["E"]),  # 37
            ("R", ["d", "[", "]"]),  # 38
            ("R", ["d", "(", ")"]),  # 39
        ]
        
        for lhs, rhs in grammar_rules:
            self.productions[lhs].append(rhs)
            self.productions_list.append((lhs, rhs))
    
    def compute_first(self):
        """计算FIRST集"""
        self.first = defaultdict(set)
        
        terminals = {'int', 'void', 'if', 'else', 'while', 'return',
                     '(', ')', '[', ']', '{', '}', ';', '=', '+', '*',
                     '∧', '∨', 'r', ',', 'd', 'i', '$', 'ε', '?', ':'}
        
        for t in terminals:
            self.first[t].add(t)
        
        changed = True
        while changed:
            changed = False
            for lhs in self.productions:
                old_size = len(self.first[lhs])
                
                for rhs in self.productions[lhs]:
                    if rhs == ['ε']:
                        self.first[lhs].add('ε')
                    else:
                        all_have_epsilon = True
                        for symbol in rhs:
                            self.first[lhs].update(self.first[symbol] - {'ε'})
                            if 'ε' not in self.first[symbol]:
                                all_have_epsilon = False
                                break
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
                        if symbol in self.productions:
                            old_size = len(self.follow[symbol])
                            
                            beta = rhs[i + 1:]
                            
                            if not beta:
                                self.follow[symbol].update(self.follow[lhs])
                            else:
                                first_beta = set()
                                all_epsilon = True
                                
                                for b_sym in beta:
                                    first_beta.update(self.first[b_sym] - {'ε'})
                                    if 'ε' not in self.first[b_sym]:
                                        all_epsilon = False
                                        break
                                
                                self.follow[symbol].update(first_beta)
                                if all_epsilon:
                                    self.follow[symbol].update(self.follow[lhs])
                            
                            if len(self.follow[symbol]) > old_size:
                                changed = True
        
        self.follow['Q'].add('}')
        self.follow['S'].update({'}', ';', 'else'})
        # Add ? and : to FOLLOW sets for ternary operator
        self.follow['E'].update({'?', ':', ')', ';', '}', ',', 'r', '+', '*', '∧', '∨'})


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
        return self.dot >= len(self.rhs) or (len(self.rhs) == 1 and self.rhs[0] == 'ε')
    
    def next_symbol(self):
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
        closure_set = set(items)
        changed = True
        
        while changed:
            changed = False
            new_items = set()
            
            for item in closure_set:
                next_sym = item.next_symbol()
                if next_sym and next_sym in self.grammar.productions:
                    for prod in self.grammar.productions[next_sym]:
                        new_item = Item(next_sym, prod, 0)
                        if new_item not in closure_set:
                            new_items.add(new_item)
            
            if new_items:
                closure_set.update(new_items)
                changed = True
        
        return frozenset(closure_set)
    
    def goto(self, items, symbol):
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
        start_item = Item(self.start_symbol, self.grammar.productions[self.start_symbol][0], 0)
        start_state = self.closure([start_item])
        
        self.states = [start_state]
        
        all_symbols = set()
        for prods in self.grammar.productions.values():
            for prod in prods:
                for sym in prod:
                    if sym != 'ε':
                        all_symbols.add(sym)
        
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
        terminals = {'int', 'void', 'if', 'else', 'while', 'return',
                     '(', ')', '[', ']', '{', '}', ';', '=', '+', '*',
                     '∧', '∨', 'r', ',', 'd', 'i', '$', '?', ':'}
        nonterminals = set(self.grammar.productions.keys())
        
        for i in range(len(self.states)):
            self.action_table[i] = {}
            self.goto_table[i] = {}
        
        for state_idx, state in enumerate(self.states):
            for item in state:
                if not item.is_complete():
                    next_sym = item.next_symbol()
                    if next_sym and (state_idx, next_sym) in self.transitions:
                        next_state = self.transitions[(state_idx, next_sym)]
                        
                        if next_sym in terminals:
                            if next_sym in self.action_table[state_idx]:
                                print(f"移进/归约冲突在状态{state_idx}, 符号'{next_sym}'")
                            else:
                                self.action_table[state_idx][next_sym] = f"s{next_state}"
                        elif next_sym in nonterminals:
                            self.goto_table[state_idx][next_sym] = next_state
                else:
                    if (item.lhs == self.start_symbol and
                            item.rhs == self.grammar.productions[self.start_symbol][0]):
                        self.action_table[state_idx]['$'] = 'acc'
                    else:
                        prod = (item.lhs, item.rhs)
                        try:
                            prod_idx = self.grammar.productions_list.index(prod)
                            for follow_sym in self.grammar.follow[item.lhs]:
                                if follow_sym in self.action_table[state_idx]:
                                    print(f"归约/归约冲突在状态{state_idx}, 符号'{follow_sym}'")
                                else:
                                    self.action_table[state_idx][follow_sym] = f"r{prod_idx}"
                        except ValueError:
                            print(f"警告：找不到产生式 {prod}")
    
    def build_parser(self):
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
        self.intermediate_code = []  # Store quadruples
        self.temp_count = 0  # Counter for temporary variables
        self.label_count = 0  # Counter for labels
    
    def new_temp(self):
        """Generate a new temporary variable"""
        self.temp_count += 1
        return f"t{self.temp_count}"
    
    def new_label(self):
        """Generate a new label"""
        self.label_count += 1
        return f"L{self.label_count}"
    
    def parse_tokens(self, token_lines: List[str]) -> List[Tuple[str, str]]:
        tokens = []
        for line in token_lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('(') and line.endswith(')'):
                content = line[1:-1]
                comma_pos = content.find(', ')
                if comma_pos != -1:
                    token_type = content[:comma_pos].strip()
                    token_val = content[comma_pos + 2:].strip()
                    tokens.append((token_type, token_val))
                    continue
            
            print(f"警告：无法解析token行: {line}")
        
        if not tokens or tokens[-1] != ("$", "$"):
            tokens.append(("$", "$"))
        return tokens
    
    def parse(self, tokens: List[Tuple[str, str]]) -> bool:
        if self.debug:
            print("\n=== 映射后的终结符序列 ===")
            for i, (token_type, token_val) in enumerate(tokens):
                mapped = TokenMapper.map_token_to_symbol(token_type, token_val)
                print(f"{i:2d}: ({token_type:8}, {token_val:10}) -> '{mapped}'")
        
        state_stack = [0]
        symbol_stack = []
        value_stack = []
        token_index = 0
        step = 0
        
        if self.debug:
            print(f"\n=== 语法分析过程 ===")
            print(f"{'步骤':<4} {'状态栈':<20} {'符号栈':<25} {'输入':<15} {'动作':<15} {'中间代码':<30}")
            print("-" * 100)
        
        while token_index < len(tokens):
            current_state = state_stack[-1]
            token_type, token_val = tokens[token_index]
            current_symbol = TokenMapper.map_token_to_symbol(token_type, token_val)
            
            action = self.parser.action_table[current_state].get(current_symbol)
            
            code_gen = ""  # Intermediate code for this step
            
            if self.debug:
                state_str = str(state_stack)
                symbol_str = str(symbol_stack)
                input_str = f"{current_symbol}({token_val})"
                action_str = action if action else "ERROR"
                print(f"{step:<4} {state_str:<20} {symbol_str:<25} {input_str:<15} {action_str:<15} {code_gen:<30}")
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
                
                pop_count = 0 if rhs == ['ε'] else len(rhs)
                popped_values = []
                
                if pop_count > 0:
                    popped_values = value_stack[-pop_count:]
                    del state_stack[-pop_count:]
                    del symbol_stack[-pop_count:]
                    del value_stack[-pop_count:]
                
                # Generate intermediate code for specific productions
                if lhs == "E":
                    if prod_idx == 27:  # E -> d = E
                        var, _, expr = popped_values
                        self.intermediate_code.append(("=", expr, None, var))
                        value_stack.append(var)
                    elif prod_idx == 28:  # E -> i
                        value_stack.append(popped_values[0])
                    elif prod_idx == 29:  # E -> d
                        value_stack.append(popped_values[0])
                    elif prod_idx == 30:  # E -> d ( M )
                        value_stack.append(popped_values[0])
                    elif prod_idx == 31:  # E -> E + E
                        e1, _, e2 = popped_values
                        temp = self.new_temp()
                        self.intermediate_code.append(("+", e1, e2, temp))
                        value_stack.append(temp)
                    elif prod_idx == 32:  # E -> E * E
                        e1, _, e2 = popped_values
                        temp = self.new_temp()
                        self.intermediate_code.append(("*", e1, e2, temp))
                        value_stack.append(temp)
                    elif prod_idx == 33:  # E -> ( E )
                        value_stack.append(popped_values[1])
                    elif prod_idx == 34:  # E -> E ? E : E
                        cond, _, true_val, _, false_val = popped_values
                        result = self.new_temp()
                        true_label = self.new_label()
                        false_label = self.new_label()
                        end_label = self.new_label()
                        # Generate quadruples for ternary
                        self.intermediate_code.append(("if", cond, None, true_label))
                        self.intermediate_code.append(("=", true_val, None, result))
                        self.intermediate_code.append(("goto", None, None, end_label))
                        self.intermediate_code.append(("label", false_label, None, None))
                        self.intermediate_code.append(("=", false_val, None, result))
                        self.intermediate_code.append(("label", end_label, None, None))
                        value_stack.append(result)
                elif lhs == "S" and prod_idx == 16:  # S -> d = E
                    var, _, expr = popped_values
                    self.intermediate_code.append(("=", expr, None, var))
                    value_stack.append("")
                elif lhs == "S" and prod_idx == 20:  # S -> return E
                    expr = popped_values[1]
                    self.intermediate_code.append(("return", expr, None, None))
                    value_stack.append("")
                else:
                    value_stack.append("")
                
                symbol_stack.append(lhs)
                
                current_state = state_stack[-1]
                goto_state = self.parser.goto_table[current_state].get(lhs)
                
                if goto_state is None:
                    print(f"GOTO错误：在状态 {current_state} 找不到符号 '{lhs}' 的转移")
                    print(f"可用GOTO: {list(self.parser.goto_table[current_state].keys())}")
                    return False
                
                state_stack.append(goto_state)
            
            elif action == "acc":
                if self.debug:
                    print("\n=== 分析成功！ ===")
                    print("\n=== 中间代码（四元式） ===")
                    for i, quad in enumerate(self.intermediate_code, 1):
                        print(f"{i:2d}: {quad}")
                return True
            
            else:
                print(f"未知动作：{action}")
                return False
        
        return False


def main():
    """主函数"""
    print("=== SLR(1)语法分析器 ===")
    
    try:
        with open("output.txt", "r", encoding="utf-8") as f:
            token_lines = f.readlines()
        
        engine = SLRParserEngine()
        tokens = engine.parse_tokens(token_lines)
        
        print("=== 开始SLR语法分析 ===")
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
    main()
