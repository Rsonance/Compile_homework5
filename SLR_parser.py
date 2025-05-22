#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：Compile_homework5 
@File    ：SLR_parser.py
@IDE     ：PyCharm 
@Author  ：ZCTong
@Date    ：2025/5/22 14:35 
"""

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
    """将 token 流转为 [(symbol, value), ...]"""
    tokens = []
    for line in token_lines:
        line = line.strip()
        if line:
            sym, val = line.strip("()\n ").split(",", 1)
            tokens.append((sym.strip(), val.strip()))
    tokens.append(("$", "$"))  # 结束符
    return tokens

def parse(tokens):
    state_stack = [0]
    symbol_stack = []
    value_stack = []

    index = 0
    while True:
        state = state_stack[-1]
        token_type, token_val = tokens[index]
        action = action_table.get((state, token_type))
        if action is None:
            print(f"语法错误 at token {token_type} ({token_val}) in state {state}")
            break

        if action[0] == "s":  # 移入
            next_state = int(action[1:])
            state_stack.append(next_state)
            symbol_stack.append(token_type)
            value_stack.append(token_val)
            index += 1
        elif action[0] == "r":  # 规约
            prod_index = int(action[1:])
            lhs, rhs = productions[prod_index]
            rhs_len = len(rhs)
            args = value_stack[-rhs_len:] if rhs_len > 0 else []

            # 弹出
            del state_stack[-rhs_len:]
            del symbol_stack[-rhs_len:]
            del value_stack[-rhs_len:]

            # 处理规约语义动作（简单示例，需根据具体产生式拓展）
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

            elif lhs == "S" and rhs == ["d", "=", "E"]:
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