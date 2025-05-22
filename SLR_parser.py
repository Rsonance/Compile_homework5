#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：Compile_homework5 
@File    ：SLR_parser.py
@IDE     ：PyCharm 
@Author  ：ZCTong
@Date    ：2025/5/22 14:35 
"""

import re
from table_of_SLR import action_table, goto_table, productions

# 三元式中间代码
three_address_code = []
temp_var_count = 0

def new_temp():
    global temp_var_count
    temp = f"t{temp_var_count}"
    temp_var_count += 1
    return temp

def parse_tokens(token_lines):
    """将 token 文件内容转为 [(token_type, token_val), ...] 格式"""
    tokens = []
    for line in token_lines:
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^\(\s*(\w+)\s*,\s*(.*?)\s*\)\s*$", line)

        if match:
            token_type, token_val = match.groups()
            tokens.append((token_type, token_val))
        else:
            print(f"无法解析 token 行: {line}")
    tokens.append(("$", "$"))  # 结束符
    return tokens

def map_token_to_symbol(token_type, token_val):
    """将词法 token 映射为语法分析用的终结符"""
    if token_type == "ID":
        return "d"
    elif token_type == "NUMBER":
        return "i"
    elif token_type == "KEY":
        return token_val  # 如 int, return
    elif token_type in {"LPA", "RPA", "LBR", "RBR", "SCO", "ASG"}:
        return token_val  # 如 (, ), {, }, ;, =
    else:
        return token_val  # 默认按原值处理

def parse(tokens):
    #print("\n映射后的终结符序列：")
    #for i, (token_type, token_val) in enumerate(tokens):
    #    mapped = map_token_to_symbol(token_type, token_val)
    #    print(f"{i}: ({token_type}, {token_val}) -> '{mapped}'")

    state_stack = [1]
    symbol_stack = []
    value_stack = []

    index = 0
    while True:
        state = state_stack[-1]
        token_type, token_val = tokens[index]
        symbol = map_token_to_symbol(token_type, token_val)
        action = action_table.get((state, symbol))

        if action is None:
            print(f"语法错误 at token {token_type} ({token_val}) in state {state}")
            break

        if action.startswith("s"):  # 移入
            next_state = int(action[1:])
            state_stack.append(next_state)
            symbol_stack.append(symbol)
            value_stack.append(token_val)
            index += 1
        elif action.startswith("r"):  # 规约
            prod_index = int(action[1:])
            lhs, rhs = productions[prod_index]
            rhs_len = len(rhs)
            args = value_stack[-rhs_len:] if rhs_len > 0 else []

            # 弹出
            del state_stack[-rhs_len:]
            del symbol_stack[-rhs_len:]
            del value_stack[-rhs_len:]

            # 简单语义动作（示例）
            if lhs == "E":
                if rhs == ["E", "+", "E"]:
                    t2 = args.pop()
                    t1 = args.pop()
                    t = new_temp()
                    three_address_code.append((t, "=", t1, "+", t2))
                    args = [t]
                elif rhs == ["E", "*", "E"]:
                    t2 = args.pop()
                    t1 = args.pop()
                    t = new_temp()
                    three_address_code.append((t, "=", t1, "*", t2))
                    args = [t]
                elif rhs == ["(", "E", ")"]:
                    args = [args[1]]
                elif len(rhs) == 1:
                    args = [args[0]]

            elif lhs == "S" and rhs == ["id", "=", "E"]:
                var = args[0]
                val = args[2]
                three_address_code.append((var, "=", val))
                args = []

            # 入栈
            symbol_stack.append(lhs)
            goto_state = goto_table.get((state_stack[-1], lhs))
            if goto_state is None:
                print(f"GOTO 错误：在状态 {state_stack[-1]} 下找不到 {lhs}")
                break
            state_stack.append(goto_state)
            value_stack.append(args[0] if args else "")
        elif action == "acc":
            print("分析成功")
            return
        else:
            print(f"未知动作: {action}")
            break

def print_three_address_code():
    print("\n三元式中间代码：")
    for instr in three_address_code:
        if len(instr) == 3:
            print(f"{instr[0]} = {instr[2]}")
        elif len(instr) == 5:
            print(f"{instr[0]} = {instr[2]} {instr[3]} {instr[4]}")
        else:
            print(instr)

if __name__ == "__main__":
    with open("output.txt", "r", encoding="utf-8") as f:
        token_lines = f.readlines()
    tokens = parse_tokens(token_lines)
    parse(tokens)
    print_three_address_code()
