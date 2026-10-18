"""通过模拟玩家输入，检查一整轮游戏的行为。"""

import contextlib
import io
import random
import unittest
from copy import deepcopy
from unittest.mock import patch

import game
from questions import QUESTIONS


class GameTests(unittest.TestCase):
    def question_order(self, questions, count=None):
        """固定测试用的随机种子，预测题序，避免测试偶然失败。"""
        if count is None:
            count = len(questions)
        return random.Random(42).sample(questions, k=count)

    def play(self, answers, menu_inputs=None, count_inputs=None):
        if menu_inputs is None:
            menu_inputs = ["1"]
        if count_inputs is None:
            count_inputs = [""]
        output = io.StringIO()
        inputs = list(menu_inputs) + list(count_inputs) + list(answers)
        with patch("builtins.input", side_effect=inputs):
            # 仍使用真实的随机抽样算法，只在测试中固定种子。
            with patch("game.random", random.Random(42)):
                with contextlib.redirect_stdout(output):
                    game.main()
        return output.getvalue()

    def test_full_round_all_correct(self):
        output = self.play([question["answer"] for question in self.question_order(QUESTIONS)])
        total = len(QUESTIONS)
        maximum = total * game.POINTS_PER_QUESTION
        self.assertIn(f"已完成：{total}/{total} 题", output)
        self.assertIn(f"答对：{total}/{total} 题", output)
        self.assertIn(f"得分：{maximum}/{maximum} 分", output)
        self.assertIn("已答题正确率：100%", output)
        self.assertEqual(output.count("解析："), total)
        self.assertNotIn("本轮错题回顾", output)

    def test_all_wrong_answers_appear_in_review(self):
        answers = [
            next(option for option in question["options"] if option != question["answer"])
            for question in self.question_order(QUESTIONS)
        ]
        output = self.play(answers)
        total = len(QUESTIONS)
        self.assertIn(f"答对：0/{total} 题", output)
        self.assertIn(f"得分：0/{total * game.POINTS_PER_QUESTION} 分", output)
        review = output.split("本轮错题回顾：", 1)[1]
        for question in QUESTIONS:
            self.assertIn(question["prompt"], review)
            self.assertIn(question["explanation"], review)

    def test_invalid_input_retries_then_accepts_lowercase(self):
        first_question = self.question_order(QUESTIONS)[0]
        output = self.play(["", "不确定", "5", f" {first_question['answer'].lower()} ", "q"])
        self.assertEqual(output.count("输入无效"), 3)
        self.assertIn("答对：1/1 题", output)
        self.assertIn(f"已完成：1/{len(QUESTIONS)} 题", output)
        self.assertIn("本轮提前结束", output)

    def test_numeric_answers_and_partial_round_accuracy(self):
        ordered = self.question_order(QUESTIONS)
        first_answer = str(list("ABCD").index(ordered[0]["answer"]) + 1)
        wrong_answer = next(
            option for option in ordered[1]["options"]
            if option != ordered[1]["answer"]
        )
        output = self.play([first_answer, wrong_answer, "Q"])
        self.assertIn("答对：1/2 题", output)
        self.assertIn("已答题正确率：50%", output)
        self.assertIn(f"得分：{game.POINTS_PER_QUESTION}/", output)
        self.assertNotIn("恭喜完成本轮挑战", output)

    def test_quit_without_answer_has_no_division_by_zero(self):
        output = self.play(["Q"])
        self.assertIn("答对：0/0 题", output)
        self.assertIn("本轮尚未作答", output)
        self.assertNotIn("已答题正确率", output)

    def test_closed_input_and_keyboard_interrupt_finish_cleanly(self):
        for interruption in (EOFError(), KeyboardInterrupt()):
            with self.subTest(interruption=type(interruption).__name__):
                first_question = self.question_order(QUESTIONS)[0]
                output = self.play([first_question["answer"], interruption])
                self.assertIn("答题结束", output)
                self.assertIn("答对：1/1 题", output)

    def test_category_games_use_only_selected_questions(self):
        for choice, topic in [("2", "生理学"), ("3", "医学统计")]:
            with self.subTest(topic=topic):
                selected = [question for question in QUESTIONS if question["topic"] == topic]
                output = self.play(
                    [question["answer"] for question in self.question_order(selected)],
                    menu_inputs=[choice],
                )
                total = len(selected)
                maximum = total * game.POINTS_PER_QUESTION
                self.assertIn(f"共 {total} 题", output)
                self.assertIn(f"已完成：{total}/{total} 题", output)
                self.assertIn(f"得分：{maximum}/{maximum} 分", output)
                for question in QUESTIONS:
                    if question["topic"] == topic:
                        self.assertIn(question["prompt"], output)
                    else:
                        self.assertNotIn(question["prompt"], output)

    def test_menu_retries_invalid_input_before_starting(self):
        selected = [question for question in QUESTIONS if question["topic"] == "生理学"]
        first_question = self.question_order(selected)[0]
        output = self.play(
            [first_question["answer"], "Q"],
            menu_inputs=["", "4", "不确定", " 2 "],
        )
        self.assertEqual(output.count("输入无效，请重新选择。"), 3)
        self.assertIn(f"已完成：1/{len(selected)} 题", output)
        self.assertIn("答对：1/1 题", output)

    def test_quit_at_menu_does_not_start_a_round(self):
        output = self.play([], menu_inputs=[" q "])
        self.assertIn("请选择题目分类", output)
        self.assertNotIn("第 1/", output)
        self.assertNotIn("本轮成绩", output)

    def test_closed_menu_input_and_keyboard_interrupt_finish_cleanly(self):
        for interruption in (EOFError(), KeyboardInterrupt()):
            with self.subTest(interruption=type(interruption).__name__):
                output = self.play([], menu_inputs=[interruption])
                self.assertIn("已退出。", output)
                self.assertNotIn("本轮成绩", output)

    def test_partial_category_round_uses_category_maximum_and_reviews_mistakes(self):
        selected = [question for question in QUESTIONS if question["topic"] == "医学统计"]
        ordered = self.question_order(selected)
        wrong = next(option for option in ordered[1]["options"] if option != ordered[1]["answer"])
        output = self.play([ordered[0]["answer"], wrong, "Q"], menu_inputs=["3"])
        self.assertIn(f"已完成：2/{len(selected)} 题", output)
        self.assertIn("答对：1/2 题", output)
        self.assertIn(
            f"得分：{game.POINTS_PER_QUESTION}/{len(selected) * game.POINTS_PER_QUESTION} 分",
            output,
        )
        self.assertIn("已答题正确率：50%", output)
        self.assertIn("回顾一下错题，下次继续进步！", output)
        review = output.split("本轮错题回顾：", 1)[1]
        self.assertIn(ordered[1]["prompt"], review)
        self.assertNotIn(ordered[0]["prompt"], review)
        self.assertNotIn("恭喜完成本轮挑战", output)

    def test_random_order_is_displayed_without_losing_questions_or_changing_bank(self):
        original_bank = deepcopy(QUESTIONS)
        for choice, topic in [("1", None), ("2", "生理学"), ("3", "医学统计")]:
            with self.subTest(topic=topic):
                selected = [
                    question for question in QUESTIONS
                    if topic is None or question["topic"] == topic
                ]
                ordered = self.question_order(selected)
                self.assertNotEqual(ordered, selected)
                output = self.play([question["answer"] for question in ordered], menu_inputs=[choice])
                positions = [output.index(question["prompt"]) for question in ordered]
                self.assertEqual(positions, sorted(positions))
                for question in selected:
                    self.assertEqual(output.count(question["prompt"]), 1)
                self.assertEqual(QUESTIONS, original_bank)

    def test_custom_counts_use_only_sampled_questions_and_correct_maximum(self):
        original_bank = deepcopy(QUESTIONS)
        physiology_count = sum(question["topic"] == "生理学" for question in QUESTIONS)
        statistics_count = sum(question["topic"] == "医学统计" for question in QUESTIONS)
        cases = [
            ("1", None, 1, "1"),
            ("1", None, len(QUESTIONS), str(len(QUESTIONS))),
            ("2", "生理学", 3, "3"),
            ("2", "生理学", physiology_count, str(physiology_count)),
            ("2", "生理学", physiology_count, "   "),
            ("3", "医学统计", 2, "2"),
            ("3", "医学统计", statistics_count, str(statistics_count)),
        ]
        for choice, topic, count, count_input in cases:
            with self.subTest(choice=choice, count=count, count_input=count_input):
                selected = [
                    question for question in QUESTIONS
                    if topic is None or question["topic"] == topic
                ]
                ordered = self.question_order(selected, count)
                output = self.play(
                    [question["answer"] for question in ordered],
                    menu_inputs=[choice],
                    count_inputs=[count_input],
                )
                maximum = count * game.POINTS_PER_QUESTION
                self.assertIn(f"本轮共 {count} 题", output)
                self.assertIn(f"满分 {maximum} 分", output)
                self.assertIn(f"已完成：{count}/{count} 题", output)
                self.assertIn(f"答对：{count}/{count} 题", output)
                self.assertIn(f"得分：{maximum}/{maximum} 分", output)
                self.assertIn(f"第 {count}/{count} 题", output)
                positions = [output.index(question["prompt"]) for question in ordered]
                self.assertEqual(positions, sorted(positions))
                for question in QUESTIONS:
                    expected_occurrences = 1 if question in ordered else 0
                    self.assertEqual(output.count(question["prompt"]), expected_occurrences)
                self.assertEqual(QUESTIONS, original_bank)

    def test_count_retries_invalid_numbers_and_text(self):
        selected = [question for question in QUESTIONS if question["topic"] == "生理学"]
        ordered = self.question_order(selected, 3)
        output = self.play(
            [question["answer"] for question in ordered],
            menu_inputs=["2"],
            count_inputs=["0", "-1", str(len(selected) + 1), "不确定", "2.5", " 3 "],
        )
        self.assertEqual(output.count(f"题数必须在 1～{len(selected)} 之间"), 3)
        self.assertEqual(output.count("请输入整数"), 2)
        self.assertIn("已完成：3/3 题", output)
        self.assertIn("得分：60/60 分", output)

    def test_quit_at_count_selection_does_not_start_a_round(self):
        output = self.play([], count_inputs=[" q "])
        self.assertIn("已退出。", output)
        self.assertNotIn("第 1/", output)
        self.assertNotIn("本轮成绩", output)

    def test_closed_count_input_and_keyboard_interrupt_finish_cleanly(self):
        for interruption in (EOFError(), KeyboardInterrupt()):
            with self.subTest(interruption=type(interruption).__name__):
                output = self.play([], count_inputs=[interruption])
                self.assertIn("已退出。", output)
                self.assertNotIn("本轮成绩", output)

    def test_partial_custom_round_scores_and_reviews_only_answered_questions(self):
        selected = [question for question in QUESTIONS if question["topic"] == "生理学"]
        ordered = self.question_order(selected, 3)
        wrong = next(option for option in ordered[1]["options"] if option != ordered[1]["answer"])
        output = self.play(
            [ordered[0]["answer"], wrong, "Q"],
            menu_inputs=["2"],
            count_inputs=["3"],
        )
        self.assertIn("已完成：2/3 题", output)
        self.assertIn("答对：1/2 题", output)
        self.assertIn("已答题正确率：50%", output)
        self.assertIn(f"得分：{game.POINTS_PER_QUESTION}/{3 * game.POINTS_PER_QUESTION} 分", output)
        self.assertNotIn("恭喜完成本轮挑战", output)
        review = output.split("本轮错题回顾：", 1)[1]
        self.assertIn(ordered[1]["prompt"], review)
        self.assertNotIn(ordered[0]["prompt"], review)
        self.assertNotIn(ordered[2]["prompt"], review)

    def test_question_bank_has_valid_content(self):
        self.assertGreaterEqual(len(QUESTIONS), 5)
        prompts = set()
        for question in QUESTIONS:
            with self.subTest(prompt=question["prompt"]):
                self.assertEqual(set(question["options"]), set("ABCD"))
                self.assertIn(question["answer"], question["options"])
                self.assertTrue(question["topic"].strip())
                self.assertTrue(question["prompt"].strip())
                self.assertTrue(question["explanation"].strip())
                self.assertTrue(all(text.strip() for text in question["options"].values()))
                self.assertNotIn(question["prompt"], prompts)
                prompts.add(question["prompt"])


if __name__ == "__main__":
    unittest.main()
