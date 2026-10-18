"""医学知识闯关游戏：在终端运行 python3 game.py。"""

import json
import random
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from questions import QUESTIONS


POINTS_PER_QUESTION = 20
HISTORY_PATH = Path(__file__).resolve().parent / "data" / "history.json"

def filter_questions(questions, topic):
    selected_questions = []

    for question in questions:
        if question["topic"] == topic:
            selected_questions.append(question)

    return selected_questions

def choose_questions():
    print("请选择题目分类：")
    print("1. 全部题目")
    print("2. 生理学")
    print("3. 医学统计")

    while True:
        try:
            choice = input("输入 1、2、3，或 Q 退出：").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return []

        if choice == "1":
            return QUESTIONS
        elif choice == "2":
            return filter_questions(QUESTIONS, "生理学")
        elif choice == "3":
            return filter_questions(QUESTIONS, "医学统计")
        elif choice == "Q":
            return []
        else:
            print("输入无效，请重新选择。")


def choose_question_count(total):
    """获取本轮题数；回车选择全部，退出时返回 None。"""
    print(f"该分类共有 {total} 道题。")

    while True:
        try:
            choice = input(
                f"本轮答几题？输入 1～{total}，回车选择全部，Q 退出："
            ).strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return None

        if choice == "Q":
            print("已退出。")
            return None
        if choice == "":
            return total

        try:
            count = int(choice)
        except ValueError:
            print("请输入整数，或直接回车选择全部；输入 Q 可退出。")
            continue

        if 1 <= count <= total:
            return count

        print(f"题数必须在 1～{total} 之间，请重新输入。")


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
    """显示成绩和本轮错题，并返回用于保存的成绩字典。"""
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
    accuracy = correct_count / answered_count * 100 if answered_count > 0 else None
    print("\n========== 本轮成绩 ==========")
    print(f"已完成：{answered_count}/{total} 题")
    print(f"答对：{correct_count}/{answered_count} 题")
    print(f"得分：{score}/{total * POINTS_PER_QUESTION} 分")

    if answered_count > 0:
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

    return {
        "total": total,
        "answered_count": answered_count,
        "correct_count": correct_count,
        "score": score,
        "maximum": total * POINTS_PER_QUESTION,
        "accuracy": accuracy,
    }


def save_result(summary):
    """追加保存一轮成绩和带时区的 UTC 时间，返回是否保存成功。"""
    if summary["answered_count"] == 0:
        return False

    try:
        if HISTORY_PATH.exists():
            history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        else:
            history = []

        if not isinstance(history, list):
            raise ValueError("历史成绩必须是一个列表")

        record = summary.copy()
        record["saved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        history.append(record)

        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        # 先写入同一目录下的临时文件，写完再替换，保护已有成绩。
        with tempfile.TemporaryDirectory(prefix=".history-", dir=HISTORY_PATH.parent) as temporary_directory:
            temporary_path = Path(temporary_directory) / "history.json"
            temporary_path.write_text(
                json.dumps(history, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(HISTORY_PATH)
    except (ValueError, UnicodeError):
        print("历史成绩文件格式有误，本轮成绩未保存，原文件保持不变。")
        return False
    except OSError as error:
        print(f"成绩保存失败：{error}。本轮成绩仍可在上方查看。")
        return False

    print("本轮成绩已保存到 data/history.json。")
    return True


def main():
    print("========== 医学知识闯关 ==========")

    selected_questions = choose_questions()
    if not selected_questions:
        return

    count = choose_question_count(len(selected_questions))
    if count is None:
        return

    # 随机抽取指定数量的题目，生成新列表，保留原题库的顺序。
    selected_questions = random.sample(
        selected_questions,
        k=count,
    )

    maximum = len(selected_questions) * POINTS_PER_QUESTION
    print(f"本轮共 {len(selected_questions)} 题，每题 {POINTS_PER_QUESTION} 分，满分 {maximum} 分。")
    print("输入字母或数字选择答案，输入 Q 可提前结束。")
    print("本轮成绩会保存到当前环境的 data/history.json；错题回顾仅限本轮。")

    results = []
    for number, question in enumerate(selected_questions, start=1):
        answer = ask_question(question, number, len(selected_questions))
        if answer is None:
            break

        results.append({"question": question, "answer": answer})
        if answer == question["answer"]:
            print(f"答对了！+{POINTS_PER_QUESTION} 分")
        else:
            expected = question["answer"]
            print(f"这题答错了。正确答案：{expected}. {question['options'][expected]}")
        print(f"解析：{question['explanation']}")

    summary = show_summary(results, len(selected_questions))
    save_result(summary)


if __name__ == "__main__":
    main()
