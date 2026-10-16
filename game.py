"""医学知识闯关游戏：在终端运行 python3 game.py。"""

from questions import QUESTIONS


POINTS_PER_QUESTION = 20


def ask_question(question, number, total):
    """显示一道题，返回有效答案；退出时返回 None。"""
    print(f"\n第 {number}/{total} 题 · {question['topic']}")
    print(question["prompt"])
    for label, text in question["options"].items():
        print(f"  {label}. {text}")

    # 无效输入只会重新提问，不会扣分或跳过当前题。
    number_to_letter = {"1": "A", "2": "B", "3": "C", "4": "D"}
    while True:
        try:
            answer = input("你的答案（A-D 或 1-4，Q 退出）：").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\n答题结束。")
            return None

        if answer == "Q":
            return None

        answer = number_to_letter.get(answer, answer)
        if answer in question["options"]:
            return answer

        print("输入无效，请输入 A、B、C、D 或 1、2、3、4；也可以输入 Q 退出。")


def show_summary(results, total):
    """根据已经提交的答案统计成绩，并列出本轮错题。"""
    correct_count = 0
    mistakes = []
    for result in results:
        question = result["question"]
        if result["answer"] == question["answer"]:
            correct_count += 1
        else:
            mistakes.append(result)

    answered_count = len(results)
    score = correct_count * POINTS_PER_QUESTION
    print("\n========== 本轮成绩 ==========")
    print(f"已完成：{answered_count}/{total} 题")
    print(f"答对：{correct_count}/{answered_count} 题")
    print(f"得分：{score}/{total * POINTS_PER_QUESTION} 分")

    if answered_count > 0:
        accuracy = correct_count / answered_count * 100
        print(f"已答题正确率：{accuracy:.0f}%")
        if accuracy >= 80:
            print("本轮表现不错，继续挑战！")
        else:
            print("回顾一下错题，下次继续进步！")
    else:
        print("本轮尚未作答，可以重新运行游戏开始挑战。")

    if answered_count == total and total > 0:
        print("恭喜完成本轮挑战！")
    elif answered_count > 0:
        print("本轮提前结束，未答题不计入正确率。")

    if mistakes:
        print("\n本轮错题回顾：")
        for number, result in enumerate(mistakes, start=1):
            question = result["question"]
            chosen = result["answer"]
            expected = question["answer"]
            print(f"{number}. {question['prompt']}")
            print(f"   你的答案：{chosen}. {question['options'][chosen]}")
            print(f"   正确答案：{expected}. {question['options'][expected]}")
            print(f"   解析：{question['explanation']}")


def main():
    print("========== 医学知识闯关 ==========")
    print(f"共 {len(QUESTIONS)} 题，每题 {POINTS_PER_QUESTION} 分。")
    print("输入字母或数字选择答案，输入 Q 可提前结束。")
    print("答题记录仅用于本轮，关闭程序后不会保存。")

    results = []
    for number, question in enumerate(QUESTIONS, start=1):
        answer = ask_question(question, number, len(QUESTIONS))
        if answer is None:
            break

        results.append({"question": question, "answer": answer})
        if answer == question["answer"]:
            print(f"答对了！+{POINTS_PER_QUESTION} 分")
        else:
            expected = question["answer"]
            print(f"这题答错了。正确答案：{expected}. {question['options'][expected]}")
        print(f"解析：{question['explanation']}")

    show_summary(results, len(QUESTIONS))


if __name__ == "__main__":
    main()
