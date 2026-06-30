#!/usr/bin/env python3
"""Tests for quiz.py - main menu and program functions"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import quiz

# 测试用题库数据（替代已移除的硬编码 QUESTION_BANK）
SAMPLE_QUESTIONS = [
    {
        "id": 1, "type": "single",
        "question": "毛泽东思想形成和发展的时代条件是",
        "options": {"A": "A选项", "B": "B选项", "C": "C选项", "D": "D选项"},
        "answer": "A", "explanation": "测试解析"
    },
    {
        "id": 2, "type": "single",
        "question": "测试单选题2",
        "options": {"A": "A选项", "B": "B选项", "C": "C选项", "D": "D选项"},
        "answer": "B", "explanation": "测试解析"
    },
    {
        "id": 3, "type": "single",
        "question": "毛泽东思想被确立为党的指导思想是在",
        "options": {"A": "A选项", "B": "B选项", "C": "C选项", "D": "D选项"},
        "answer": "B", "explanation": "测试解析"
    },
    {
        "id": 1, "type": "multi",
        "question": "毛泽东思想的科学内涵包括",
        "options": {"A": "A选项", "B": "B选项", "C": "C选项", "D": "D选项"},
        "answer": "ABC", "explanation": "测试解析"
    },
    {
        "id": 2, "type": "multi",
        "question": "测试多选题2",
        "options": {"A": "A选项", "B": "B选项", "C": "C选项", "D": "D选项"},
        "answer": "AB", "explanation": "测试解析"
    },
]


class TestGetQuestionsByType(unittest.TestCase):
    """Tests for get_questions_by_type()"""

    def test_filter_single(self):
        """Should return only single-choice questions"""
        result = quiz.get_questions_by_type(SAMPLE_QUESTIONS, 'single')
        self.assertTrue(all(q['type'] == 'single' for q in result))
        self.assertEqual(len(result), 3)

    def test_filter_multi(self):
        """Should return only multi-choice questions"""
        result = quiz.get_questions_by_type(SAMPLE_QUESTIONS, 'multi')
        self.assertTrue(all(q['type'] == 'multi' for q in result))
        self.assertEqual(len(result), 2)

    def test_filter_empty_result(self):
        """Should return empty list for non-existent type"""
        result = quiz.get_questions_by_type(SAMPLE_QUESTIONS, 'essay')
        self.assertEqual(result, [])

    def test_filter_empty_input(self):
        """Should return empty list for empty input"""
        result = quiz.get_questions_by_type([], 'single')
        self.assertEqual(result, [])


class TestDisplayMenu(unittest.TestCase):
    """Tests for display_menu()"""

    @patch('builtins.print')
    @patch('os.system')
    def test_clears_screen(self, mock_system, mock_print):
        """Should clear the screen"""
        quiz.display_menu()
        mock_system.assert_called_once()

    @patch('os.system')
    @patch('builtins.print')
    def test_prints_menu_items(self, mock_print, mock_system):
        """Should print menu with all options"""
        quiz.display_menu()
        # Collect all printed text
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        # Check key menu items are present
        self.assertIn('选择题刷题系统', all_output)
        self.assertIn('顺序刷题', all_output)
        self.assertIn('随机刷题', all_output)
        self.assertIn('错题回顾', all_output)
        self.assertIn('退出', all_output)


class TestMain(unittest.TestCase):
    """Tests for main()"""

    def setUp(self):
        self._original_qb = quiz.QUESTION_BANK
        quiz.QUESTION_BANK = list(SAMPLE_QUESTIONS)
        self._mock_banks = [{
            'name': '测试题库',
            'path': '/tmp/test_bank',
            'questions': list(SAMPLE_QUESTIONS)
        }]
        self._scan_patcher = patch('quiz._scan_banks_folder', return_value=self._mock_banks)
        self._scan_patcher.start()
        real_exists = os.path.exists
        def mock_exists(path):
            if path == quiz.BANKS_FOLDER:
                return True
            return real_exists(path)
        self._exists_patcher = patch('os.path.exists', side_effect=mock_exists)
        self._exists_patcher.start()

    def tearDown(self):
        self._scan_patcher.stop()
        self._exists_patcher.stop()
        quiz.QUESTION_BANK = self._original_qb

    @patch('quiz.input', side_effect=['0'])
    @patch('quiz.print_colored')
    def test_exit_choice(self, mock_print, mock_input):
        """Should exit cleanly on choice 0"""
        quiz.main()
        # Should print goodbye message
        output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('再见', output)

    @patch('quiz.input', side_effect=['99', '', '', '', '0'])
    @patch('quiz.print_colored')
    def test_invalid_choice(self, mock_print, mock_input):
        """Should show error for invalid choice"""
        quiz.main()
        output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('无效选择', output)

    @patch('quiz.input', side_effect=EOFError)
    @patch('quiz.print_colored')
    def test_eof_exits(self, mock_print, mock_input):
        """Should handle EOFError gracefully"""
        # Should not raise
        quiz.main()

    @patch('quiz.run_quiz', return_value=(50, 42, []))
    @patch('quiz.display_stats')
    @patch('quiz.input', side_effect=['1', '1', '11', '0'])
    @patch('quiz.print_colored')
    def test_choice_1_sequential_single(self, mock_print, mock_input, mock_stats, mock_quiz):
        """Choice 1 should run sequential single-choice quiz"""
        quiz.main()
        mock_quiz.assert_called_once()
        args = mock_quiz.call_args[0]
        self.assertTrue(all(q['type'] == 'single' for q in args[0]))
        self.assertEqual(args[1], 'sequential')

    @patch('quiz.run_quiz', return_value=(50, 42, []))
    @patch('quiz.display_stats')
    @patch('quiz.input', side_effect=['1', '2', '11', '0'])
    @patch('quiz.print_colored')
    def test_choice_2_random_single(self, mock_print, mock_input, mock_stats, mock_quiz):
        """Choice 2 should run random single-choice quiz"""
        quiz.main()
        args = mock_quiz.call_args[0]
        self.assertTrue(all(q['type'] == 'single' for q in args[0]))
        self.assertEqual(args[1], 'random')

    @patch('quiz.run_quiz', return_value=(25, 20, []))
    @patch('quiz.display_stats')
    @patch('quiz.input', side_effect=['1', '3', '11', '0'])
    @patch('quiz.print_colored')
    def test_choice_3_sequential_multi(self, mock_print, mock_input, mock_stats, mock_quiz):
        """Choice 3 should run sequential multi-choice quiz"""
        quiz.main()
        args = mock_quiz.call_args[0]
        self.assertTrue(all(q['type'] == 'multi' for q in args[0]))
        self.assertEqual(args[1], 'sequential')

    @patch('quiz.run_quiz', return_value=(25, 20, []))
    @patch('quiz.display_stats')
    @patch('quiz.input', side_effect=['1', '4', '11', '0'])
    @patch('quiz.print_colored')
    def test_choice_4_random_multi(self, mock_print, mock_input, mock_stats, mock_quiz):
        """Choice 4 should run random multi-choice quiz"""
        quiz.main()
        args = mock_quiz.call_args[0]
        self.assertTrue(all(q['type'] == 'multi' for q in args[0]))
        self.assertEqual(args[1], 'random')

    @patch('quiz.run_quiz', return_value=(5, 4, []))
    @patch('quiz.display_stats')
    @patch('quiz.input', side_effect=['1', '5', '11', '0'])
    @patch('quiz.print_colored')
    def test_choice_5_sequential_all(self, mock_print, mock_input, mock_stats, mock_quiz):
        """Choice 5 should run sequential all questions quiz"""
        quiz.main()
        args = mock_quiz.call_args[0]
        self.assertEqual(len(args[0]), len(SAMPLE_QUESTIONS))
        self.assertEqual(args[1], 'sequential')

    @patch('quiz.run_quiz', return_value=(5, 4, []))
    @patch('quiz.display_stats')
    @patch('quiz.input', side_effect=['1', '6', '11', '0'])
    @patch('quiz.print_colored')
    def test_choice_6_random_all(self, mock_print, mock_input, mock_stats, mock_quiz):
        """Choice 6 should run random all questions quiz"""
        quiz.main()
        args = mock_quiz.call_args[0]
        self.assertEqual(len(args[0]), len(SAMPLE_QUESTIONS))
        self.assertEqual(args[1], 'random')

    @patch('quiz.review_bank_wrong_questions')
    @patch('quiz.input', side_effect=['1', '7', '11', '0'])
    @patch('quiz.print_colored')
    def test_choice_7_wrong_review(self, mock_print, mock_input, mock_review):
        """Choice 7 should run wrong questions review"""
        quiz.main()
        mock_review.assert_called_once()

    @patch('quiz.input', side_effect=[''])
    @patch('builtins.print')
    def test_empty_banks_shows_message(self, mock_print, mock_input):
        """Should show message when banks/ is empty"""
        with patch('quiz._scan_banks_folder', return_value=[]):
            quiz.main()
            all_output = ' '.join(str(call) for call in mock_print.call_args_list)
            self.assertIn('文件夹为空', all_output)


class TestBanksFolderChecks(unittest.TestCase):
    """Tests for banks/ folder existence and emptiness checks in main()"""

    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    @patch('os.makedirs')
    @patch('os.path.exists', return_value=False)
    def test_missing_banks_folder_creates_and_shows_message(self, mock_exists, mock_makedirs, mock_print, mock_input):
        """Should create banks/ and show message when it doesn't exist"""
        quiz.main()
        mock_makedirs.assert_called_once_with(quiz.BANKS_FOLDER, exist_ok=True)
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('未找到 banks 文件夹', all_output)
        self.assertIn('已自动创建', all_output)

    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    @patch('quiz._scan_banks_folder', return_value=[])
    @patch('os.path.exists', return_value=True)
    def test_empty_banks_folder_shows_message(self, mock_exists, mock_scan, mock_print, mock_input):
        """Should show message when banks/ is empty"""
        quiz.main()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('banks/ 文件夹为空', all_output)


class TestMainBlock(unittest.TestCase):
    """Test the if __name__ == '__main__' block exists"""

    def test_main_function_exists(self):
        """main() should be callable"""
        self.assertTrue(callable(quiz.main))

    def test_display_menu_function_exists(self):
        """display_menu() should be callable"""
        self.assertTrue(callable(quiz.display_menu))

    def test_get_questions_by_type_function_exists(self):
        """get_questions_by_type() should be callable"""
        self.assertTrue(callable(quiz.get_questions_by_type))


class TestMenuIntegration(unittest.TestCase):
    """Tests for menu integration of batch delete (Task 4)"""

    def setUp(self):
        self._original_qb = quiz.QUESTION_BANK
        quiz.QUESTION_BANK = list(SAMPLE_QUESTIONS)
        self._mock_banks = [{
            'name': '测试题库',
            'path': '/tmp/test_bank',
            'questions': list(SAMPLE_QUESTIONS)
        }]
        self._scan_patcher = patch('quiz._scan_banks_folder', return_value=self._mock_banks)
        self._scan_patcher.start()
        real_exists = os.path.exists
        def mock_exists(path):
            if path == quiz.BANKS_FOLDER:
                return True
            return real_exists(path)
        self._exists_patcher = patch('os.path.exists', side_effect=mock_exists)
        self._exists_patcher.start()

    def tearDown(self):
        self._scan_patcher.stop()
        self._exists_patcher.stop()
        quiz.QUESTION_BANK = self._original_qb

    @patch('quiz.bank_batch_delete_questions')
    @patch('quiz.input', side_effect=['1', '9', '11', '0'])
    @patch('quiz.print_colored')
    def test_choice_9_batch_delete(self, mock_print, mock_input, mock_batch):
        """Choice 9 should run batch delete"""
        quiz.main()
        mock_batch.assert_called_once()

    @patch('os.system')
    @patch('builtins.print')
    def test_menu_shows_batch_delete(self, mock_print, mock_system):
        """Menu should show batch delete option"""
        quiz.display_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('批量删题', all_output)


class TestParseSelectionInput(unittest.TestCase):
    """Tests for parse_selection_input()"""

    def test_single_number(self):
        """Should parse single number"""
        result = quiz.parse_selection_input('3', (1, 20))
        self.assertEqual(result, {3})

    def test_range(self):
        """Should parse range like 3-7"""
        result = quiz.parse_selection_input('3-7', (1, 20))
        self.assertEqual(result, {3, 4, 5, 6, 7})

    def test_comma_separated(self):
        """Should parse comma-separated numbers"""
        result = quiz.parse_selection_input('3,7,12', (1, 20))
        self.assertEqual(result, {3, 7, 12})

    def test_mixed_format(self):
        """Should parse mixed format like 3-7,12,15-18"""
        result = quiz.parse_selection_input('3-7,12,15-18', (1, 20))
        self.assertEqual(result, {3, 4, 5, 6, 7, 12, 15, 16, 17, 18})

    def test_out_of_range_ignored(self):
        """Should ignore numbers outside valid range"""
        result = quiz.parse_selection_input('3,99', (1, 20))
        self.assertEqual(result, {3})

    def test_empty_input(self):
        """Should return empty set for empty input"""
        result = quiz.parse_selection_input('', (1, 20))
        self.assertEqual(result, set())

    def test_invalid_format(self):
        """Should return empty set for invalid format"""
        result = quiz.parse_selection_input('abc', (1, 20))
        self.assertEqual(result, set())

    def test_reverse_range(self):
        """Should handle reverse range like 7-3"""
        result = quiz.parse_selection_input('7-3', (1, 20))
        self.assertEqual(result, {3, 4, 5, 6, 7})


class TestSaveDeletedQuestions(unittest.TestCase):
    """Tests for save_deleted_questions()"""

    def setUp(self):
        self.test_file = 'test_deleted_questions.json'
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @patch('quiz.DELETED_QUESTIONS_FILE', 'test_deleted_questions.json')
    def test_save_creates_file(self):
        """Should create file if not exists"""
        questions = [{'id': 1, 'type': 'single', 'question': 'test'}]
        quiz.save_deleted_questions(questions)
        self.assertTrue(os.path.exists(self.test_file))

    @patch('quiz.DELETED_QUESTIONS_FILE', 'test_deleted_questions.json')
    def test_save_format(self):
        """Should save with correct format"""
        questions = [{'id': 1, 'type': 'single', 'question': 'test', 'answer': 'A'}]
        quiz.save_deleted_questions(questions)
        with open(self.test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn('deleted', data)
        self.assertEqual(len(data['deleted']), 1)
        self.assertIn('deleted_at', data['deleted'][0])
        self.assertEqual(data['deleted'][0]['question']['id'], 1)

    @patch('quiz.DELETED_QUESTIONS_FILE', 'test_deleted_questions.json')
    def test_save_appends(self):
        """Should append to existing file"""
        questions1 = [{'id': 1, 'type': 'single', 'question': 'test1'}]
        questions2 = [{'id': 2, 'type': 'single', 'question': 'test2'}]
        quiz.save_deleted_questions(questions1)
        quiz.save_deleted_questions(questions2)
        with open(self.test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(len(data['deleted']), 2)

    @patch('quiz.DELETED_QUESTIONS_FILE', 'test_deleted_questions.json')
    def test_save_multiple(self):
        """Should save multiple questions at once"""
        questions = [
            {'id': 1, 'type': 'single', 'question': 'test1'},
            {'id': 2, 'type': 'multi', 'question': 'test2'}
        ]
        quiz.save_deleted_questions(questions)
        with open(self.test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(len(data['deleted']), 2)


class TestBatchDeleteQuestions(unittest.TestCase):
    """Tests for batch_delete_questions()"""

    @patch('quiz.input', return_value='')
    @patch('quiz.load_questions')
    @patch('quiz.print_colored')
    def test_empty_bank_shows_message(self, mock_print, mock_load, mock_input):
        """Should show message when question bank is empty"""
        mock_load.return_value = {'meta': {}, 'questions': []}
        quiz.batch_delete_questions()
        output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('题库为空', output)

    @patch('quiz.load_questions')
    @patch('quiz.input', side_effect=['q'])
    @patch('quiz.print_colored')
    def test_quit_returns(self, mock_print, mock_input, mock_load):
        """Should return to main menu on 'q'"""
        mock_load.return_value = {
            'meta': {},
            'questions': [{'id': 1, 'type': 'single', 'question': 'test', 'options': {}, 'answer': 'A'}]
        }
        quiz.batch_delete_questions()
        # Should not raise

    @patch('quiz.save_questions')
    @patch('quiz.save_deleted_questions')
    @patch('quiz.load_questions')
    @patch('quiz.input', side_effect=['1', 'done', 'y', ''])
    @patch('quiz.print_colored')
    def test_select_and_confirm_delete(self, mock_print, mock_input, mock_load, mock_save_deleted, mock_save):
        """Should delete selected questions after confirmation"""
        mock_load.return_value = {
            'meta': {'total': 2, 'single_count': 2, 'multi_count': 0},
            'questions': [
                {'id': 1, 'type': 'single', 'question': 'test1', 'options': {}, 'answer': 'A'},
                {'id': 2, 'type': 'single', 'question': 'test2', 'options': {}, 'answer': 'B'}
            ]
        }
        quiz.batch_delete_questions()
        mock_save.assert_called_once()
        mock_save_deleted.assert_called_once()
        # Verify the saved data has only 1 question left
        saved_data = mock_save.call_args[0][0]
        self.assertEqual(len(saved_data['questions']), 1)
        self.assertEqual(saved_data['questions'][0]['id'], 2)

    @patch('quiz.load_questions')
    @patch('quiz.input', side_effect=['1', 'done', 'n', '', 'q'])
    @patch('quiz.print_colored')
    def test_cancel_delete(self, mock_print, mock_input, mock_load):
        """Should not delete when user cancels"""
        mock_load.return_value = {
            'meta': {},
            'questions': [
                {'id': 1, 'type': 'single', 'question': 'test', 'options': {}, 'answer': 'A'}
            ]
        }
        with patch('quiz.save_questions') as mock_save:
            quiz.batch_delete_questions()
            mock_save.assert_not_called()


class TestCollectionsDataLayer(unittest.TestCase):
    """Tests for collections data persistence"""

    def setUp(self):
        """Clean up collections file before each test"""
        self._backup = None
        if os.path.exists(quiz.COLLECTIONS_FILE):
            with open(quiz.COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
                self._backup = f.read()
            os.remove(quiz.COLLECTIONS_FILE)

    def tearDown(self):
        """Restore collections file after each test"""
        if self._backup is not None:
            with open(quiz.COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
                f.write(self._backup)
        elif os.path.exists(quiz.COLLECTIONS_FILE):
            os.remove(quiz.COLLECTIONS_FILE)

    def test_load_collections_no_file(self):
        """Should return empty structure when file doesn't exist"""
        result = quiz.load_collections()
        self.assertEqual(result, {'collections': {}})

    def test_save_and_load_collections(self):
        """Should persist and reload collections data"""
        data = {'collections': {
            'test夹': {
                'created': '2026-06-29',
                'questions': [{'id': 1, 'type': 'single', 'added_at': '2026-06-29 10:00:00'}]
            }
        }}
        quiz.save_collections(data)
        loaded = quiz.load_collections()
        self.assertEqual(loaded, data)

    def test_load_collections_corrupt_file(self):
        """Should return empty structure on corrupt JSON"""
        with open(quiz.COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
            f.write('not valid json{{{')
        result = quiz.load_collections()
        self.assertEqual(result, {'collections': {}})

    def test_create_collection(self):
        """Should create a new collection"""
        result = quiz.create_collection('重点错题')
        self.assertTrue(result)
        data = quiz.load_collections()
        self.assertIn('重点错题', data['collections'])
        self.assertEqual(data['collections']['重点错题']['questions'], [])

    def test_create_collection_already_exists(self):
        """Should return False if collection already exists"""
        quiz.create_collection('重点错题')
        result = quiz.create_collection('重点错题')
        self.assertFalse(result)

    def test_delete_collection(self):
        """Should delete an existing collection"""
        quiz.create_collection('to_delete')
        result = quiz.delete_collection('to_delete')
        self.assertTrue(result)
        data = quiz.load_collections()
        self.assertNotIn('to_delete', data['collections'])

    def test_delete_collection_not_exists(self):
        """Should return False if collection doesn't exist"""
        result = quiz.delete_collection('nonexistent')
        self.assertFalse(result)

    def test_rename_collection(self):
        """Should rename an existing collection"""
        quiz.create_collection('old_name')
        result = quiz.rename_collection('old_name', 'new_name')
        self.assertTrue(result)
        data = quiz.load_collections()
        self.assertNotIn('old_name', data['collections'])
        self.assertIn('new_name', data['collections'])

    def test_rename_collection_old_not_exists(self):
        """Should return False if old name doesn't exist"""
        result = quiz.rename_collection('nonexistent', 'new_name')
        self.assertFalse(result)

    def test_rename_collection_new_already_exists(self):
        """Should return False if new name already exists"""
        quiz.create_collection('name1')
        quiz.create_collection('name2')
        result = quiz.rename_collection('name1', 'name2')
        self.assertFalse(result)

    def test_add_to_collection(self):
        """Should add a question to a collection"""
        quiz.create_collection('my夹')
        result = quiz.add_to_collection('my夹', 3, 'single')
        self.assertTrue(result)
        data = quiz.load_collections()
        q = data['collections']['my夹']['questions'][0]
        self.assertEqual(q['id'], 3)
        self.assertEqual(q['type'], 'single')
        self.assertIn('added_at', q)

    def test_add_to_collection_already_in(self):
        """Should return False if question already in collection"""
        quiz.create_collection('my夹')
        quiz.add_to_collection('my夹', 3, 'single')
        result = quiz.add_to_collection('my夹', 3, 'single')
        self.assertFalse(result)

    def test_add_to_collection_not_exists(self):
        """Should return False if collection doesn't exist"""
        result = quiz.add_to_collection('nonexistent', 1, 'single')
        self.assertFalse(result)

    def test_remove_from_collection(self):
        """Should remove a question from a collection"""
        quiz.create_collection('my夹')
        quiz.add_to_collection('my夹', 3, 'single')
        result = quiz.remove_from_collection('my夹', 3, 'single')
        self.assertTrue(result)
        data = quiz.load_collections()
        self.assertEqual(len(data['collections']['my夹']['questions']), 0)

    def test_remove_from_collection_not_in(self):
        """Should return False if question not in collection"""
        quiz.create_collection('my夹')
        result = quiz.remove_from_collection('my夹', 99, 'single')
        self.assertFalse(result)

    def test_find_collections_for_question(self):
        """Should return list of collection names containing the question"""
        quiz.create_collection('夹1')
        quiz.create_collection('夹2')
        quiz.add_to_collection('夹1', 3, 'single')
        quiz.add_to_collection('夹2', 3, 'single')
        quiz.add_to_collection('夹1', 5, 'multi')
        result = quiz.find_collections_for_question(3, 'single')
        self.assertEqual(sorted(result), ['夹1', '夹2'])

    def test_find_collections_for_question_none(self):
        """Should return empty list if question not in any collection"""
        result = quiz.find_collections_for_question(999, 'single')
        self.assertEqual(result, [])


class TestCollectionsMenu(unittest.TestCase):
    """Tests for collections menu integration in display_menu() and main()"""

    def setUp(self):
        """Clean up collections file before each test"""
        self._original_qb = quiz.QUESTION_BANK
        quiz.QUESTION_BANK = list(SAMPLE_QUESTIONS)
        self._mock_banks = [{
            'name': '测试题库',
            'path': '/tmp/test_bank',
            'questions': list(SAMPLE_QUESTIONS)
        }]
        self._scan_patcher = patch('quiz._scan_banks_folder', return_value=self._mock_banks)
        self._scan_patcher.start()
        self._backup = None
        if os.path.exists(quiz.COLLECTIONS_FILE):
            with open(quiz.COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
                self._backup = f.read()
            os.remove(quiz.COLLECTIONS_FILE)
        real_exists = os.path.exists
        def mock_exists(path):
            if path == quiz.BANKS_FOLDER:
                return True
            return real_exists(path)
        self._exists_patcher = patch('os.path.exists', side_effect=mock_exists)
        self._exists_patcher.start()

    def tearDown(self):
        """Restore collections file after each test"""
        self._scan_patcher.stop()
        self._exists_patcher.stop()
        quiz.QUESTION_BANK = self._original_qb
        if self._backup is not None:
            with open(quiz.COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
                f.write(self._backup)
        elif os.path.exists(quiz.COLLECTIONS_FILE):
            os.remove(quiz.COLLECTIONS_FILE)

    @patch('os.system')
    @patch('builtins.print')
    def test_menu_shows_collection_count(self, mock_print, mock_system):
        """Should display collection count in menu header"""
        quiz.create_collection('test_menu')
        quiz.display_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('收藏夹', all_output)
        self.assertIn('1', all_output)  # count of 1 collection

    @patch('os.system')
    @patch('builtins.print')
    def test_menu_shows_option_10(self, mock_print, mock_system):
        """Should show option 10 for collection management"""
        quiz.display_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('10.', all_output)
        self.assertIn('收藏夹管理', all_output)

    @patch('os.system')
    @patch('builtins.print')
    def test_menu_no_collection_line_when_empty(self, mock_print, mock_system):
        """Should not show collection count line when no collections exist"""
        quiz.display_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        # The header info should NOT contain "收藏夹" when count is 0
        # (it's only shown conditionally when collection_count > 0)
        self.assertNotIn('收藏夹：0', all_output)

    @patch('quiz.input', side_effect=['1', '10', '11', '0'])
    @patch('quiz.print_colored')
    @patch('quiz.bank_collections_menu')
    def test_main_choice_10_calls_collections_menu(self, mock_collections, mock_print, mock_input):
        """Choice 10 in main() should call bank_collections_menu()"""
        quiz.main()
        mock_collections.assert_called_once()

    @patch('quiz.input', side_effect=['1', '11', '0'])
    @patch('quiz.print_colored')
    def test_main_bank_selection_prompt(self, mock_print, mock_input):
        """Bank selection prompt should show bank list"""
        quiz.main()
        # Check that the bank selection prompt is used
        prompt_call = mock_input.call_args_list[0]
        prompt_text = prompt_call[0][0] if prompt_call[0] else ''
        self.assertIn('题库编号', prompt_text)


class TestPostAnswerCollection(unittest.TestCase):
    """Tests for post-answer collection prompt"""

    def setUp(self):
        self._backup = None
        if os.path.exists(quiz.COLLECTIONS_FILE):
            with open(quiz.COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
                self._backup = f.read()
            os.remove(quiz.COLLECTIONS_FILE)

    def tearDown(self):
        if self._backup is not None:
            with open(quiz.COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
                f.write(self._backup)
        elif os.path.exists(quiz.COLLECTIONS_FILE):
            os.remove(quiz.COLLECTIONS_FILE)

    @patch('builtins.input', return_value='')
    def test_prompt_skip_on_enter(self, mock_input):
        """Should skip collection when user presses Enter"""
        quiz.create_collection('my夹')
        question = {'id': 1, 'type': 'single'}
        quiz.prompt_collect_question(question)
        data = quiz.load_collections()
        self.assertEqual(len(data['collections']['my夹']['questions']), 0)

    @patch('builtins.input', return_value='my夹')
    def test_prompt_add_to_existing(self, mock_input):
        """Should add to existing collection by name"""
        quiz.create_collection('my夹')
        question = {'id': 1, 'type': 'single'}
        quiz.prompt_collect_question(question)
        data = quiz.load_collections()
        self.assertEqual(len(data['collections']['my夹']['questions']), 1)

    @patch('builtins.input', return_value='新夹子')
    def test_prompt_create_new_and_add(self, mock_input):
        """Should create new collection and add question"""
        question = {'id': 2, 'type': 'multi'}
        quiz.prompt_collect_question(question)
        data = quiz.load_collections()
        self.assertIn('新夹子', data['collections'])
        self.assertEqual(len(data['collections']['新夹子']['questions']), 1)

    @patch('builtins.input', side_effect=['other夹', ''])
    def test_prompt_already_in_collection(self, mock_input):
        """Should show existing collections and allow adding to another"""
        quiz.create_collection('夹1')
        quiz.create_collection('other夹')
        quiz.add_to_collection('夹1', 5, 'single')
        question = {'id': 5, 'type': 'single'}
        quiz.prompt_collect_question(question)
        data = quiz.load_collections()
        self.assertEqual(len(data['collections']['other夹']['questions']), 1)


class TestRunQuizAllowCollect(unittest.TestCase):
    """Tests for run_quiz() allow_collect parameter"""

    def setUp(self):
        self._backup = None
        if os.path.exists(quiz.COLLECTIONS_FILE):
            with open(quiz.COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
                self._backup = f.read()
            os.remove(quiz.COLLECTIONS_FILE)

    def tearDown(self):
        if self._backup is not None:
            with open(quiz.COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
                f.write(self._backup)
        elif os.path.exists(quiz.COLLECTIONS_FILE):
            os.remove(quiz.COLLECTIONS_FILE)

    @patch('quiz.prompt_collect_question')
    @patch('builtins.input', return_value='A')
    def test_run_quiz_calls_collect_by_default(self, mock_input, mock_collect):
        """Should call prompt_collect_question by default"""
        questions = [{'id': 1, 'type': 'single', 'question': 'q', 'options': ['A. a'], 'answer': 'A'}]
        quiz.run_quiz(questions, 'sequential')
        mock_collect.assert_called_once()

    @patch('quiz.prompt_collect_question')
    @patch('builtins.input', return_value='A')
    def test_run_quiz_skips_collect_when_false(self, mock_input, mock_collect):
        """Should not call prompt_collect_question when allow_collect=False"""
        questions = [{'id': 1, 'type': 'single', 'question': 'q', 'options': ['A. a'], 'answer': 'A'}]
        quiz.run_quiz(questions, 'sequential', allow_collect=False)
        mock_collect.assert_not_called()


class TestCollectionsManagementUI(unittest.TestCase):
    """Tests for collections management menu"""

    def setUp(self):
        self._backup = None
        if os.path.exists(quiz.COLLECTIONS_FILE):
            with open(quiz.COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
                self._backup = f.read()
            os.remove(quiz.COLLECTIONS_FILE)

    def tearDown(self):
        if self._backup is not None:
            with open(quiz.COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
                f.write(self._backup)
        elif os.path.exists(quiz.COLLECTIONS_FILE):
            os.remove(quiz.COLLECTIONS_FILE)

    @patch('builtins.input', side_effect=['q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_displays_empty_message(self, mock_print, mock_system, mock_input):
        """Should show message when no collections exist"""
        quiz.collections_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('暂无收藏夹', all_output)

    @patch('builtins.input', side_effect=['n', '新夹子', '', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_create_new_collection(self, mock_print, mock_system, mock_input):
        """Should create new collection via 'n' command"""
        quiz.collections_menu()
        data = quiz.load_collections()
        self.assertIn('新夹子', data['collections'])

    @patch('builtins.input', side_effect=['n', '', '', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_empty_name_rejected(self, mock_print, mock_system, mock_input):
        """Should reject empty collection name"""
        quiz.collections_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('名称不能为空', all_output)

    @patch('builtins.input', side_effect=['n', 'dup', '', 'n', 'dup', '', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_duplicate_name_rejected(self, mock_print, mock_system, mock_input):
        """Should reject duplicate collection name"""
        quiz.collections_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('已存在', all_output)

    @patch('builtins.input', side_effect=['q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_displays_collection_list(self, mock_print, mock_system, mock_input):
        """Should display existing collections with question count"""
        quiz.create_collection('测试夹')
        quiz.collections_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('测试夹', all_output)
        self.assertIn('0', all_output)  # 0 questions

    @patch('builtins.input', side_effect=['abc', '', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_invalid_input_shows_error(self, mock_print, mock_system, mock_input):
        """Should show error for invalid input"""
        quiz.collections_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('请输入序号', all_output)

    @patch('builtins.input', side_effect=['99', '', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_out_of_range_index_shows_error(self, mock_print, mock_system, mock_input):
        """Should show error for out-of-range index"""
        quiz.create_collection('夹')
        quiz.collections_menu()
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('无效序号', all_output)

    @patch('quiz.collection_detail')
    @patch('builtins.input', side_effect=['1', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_valid_index_opens_detail(self, mock_print, mock_system, mock_input, mock_detail):
        """Should call collection_detail with correct name for valid index"""
        quiz.create_collection('我的夹')
        quiz.collections_menu()
        mock_detail.assert_called_once_with('我的夹')


class TestCollectionDetail(unittest.TestCase):
    """Tests for collection detail view"""

    def setUp(self):
        self._original_qb = quiz.QUESTION_BANK
        quiz.QUESTION_BANK = list(SAMPLE_QUESTIONS)
        self._backup = None
        if os.path.exists(quiz.COLLECTIONS_FILE):
            with open(quiz.COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
                self._backup = f.read()
            os.remove(quiz.COLLECTIONS_FILE)

    def tearDown(self):
        quiz.QUESTION_BANK = self._original_qb
        if self._backup is not None:
            with open(quiz.COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
                f.write(self._backup)
        elif os.path.exists(quiz.COLLECTIONS_FILE):
            os.remove(quiz.COLLECTIONS_FILE)

    @patch('builtins.input', side_effect=['q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_displays_questions(self, mock_print, mock_system, mock_input):
        """Should display questions in the collection"""
        quiz.create_collection('my夹')
        quiz.add_to_collection('my夹', 1, 'single')
        quiz.add_to_collection('my夹', 3, 'single')
        quiz.collection_detail('my夹')
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('毛泽东思想形成', all_output)
        self.assertIn('毛泽东思想被确立', all_output)

    @patch('builtins.input', side_effect=['1', 'y', '', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_remove_question(self, mock_print, mock_system, mock_input):
        """Should remove question when user inputs number and confirms"""
        quiz.create_collection('my夹')
        quiz.add_to_collection('my夹', 1, 'single')
        quiz.collection_detail('my夹')
        data = quiz.load_collections()
        self.assertEqual(len(data['collections']['my夹']['questions']), 0)

    @patch('builtins.input', side_effect=['q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_displays_empty_message(self, mock_print, mock_system, mock_input):
        """Should show empty message when collection has no questions"""
        quiz.create_collection('my夹')
        quiz.collection_detail('my夹')
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('暂无题目', all_output)

    @patch('builtins.input', side_effect=['q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_displays_collection_name(self, mock_print, mock_system, mock_input):
        """Should display collection name in header"""
        quiz.create_collection('my夹')
        quiz.collection_detail('my夹')
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('my夹', all_output)

    @patch('builtins.input', side_effect=['d', 'y', ''])
    @patch('os.system')
    @patch('builtins.print')
    def test_delete_collection(self, mock_print, mock_system, mock_input):
        """Should delete collection when user confirms"""
        quiz.create_collection('to_delete')
        quiz.collection_detail('to_delete')
        data = quiz.load_collections()
        self.assertNotIn('to_delete', data['collections'])

    @patch('builtins.input', side_effect=['r', 'new_name', '', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_rename_collection(self, mock_print, mock_system, mock_input):
        """Should rename collection"""
        quiz.create_collection('old_name')
        quiz.collection_detail('old_name')
        data = quiz.load_collections()
        self.assertIn('new_name', data['collections'])
        self.assertNotIn('old_name', data['collections'])

    @patch('builtins.input', side_effect=['99', '', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_invalid_question_number(self, mock_print, mock_system, mock_input):
        """Should show error for invalid question number"""
        quiz.create_collection('my夹')
        quiz.add_to_collection('my夹', 1, 'single')
        quiz.collection_detail('my夹')
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('无效题号', all_output)

    @patch('builtins.input', side_effect=['abc', '', 'q'])
    @patch('os.system')
    @patch('builtins.print')
    def test_invalid_input_shows_error(self, mock_print, mock_system, mock_input):
        """Should show error for non-numeric invalid input"""
        quiz.create_collection('my夹')
        quiz.collection_detail('my夹')
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('请输入有效操作', all_output)


class TestCollectionQuiz(unittest.TestCase):
    """Tests for collection quiz mode"""

    def setUp(self):
        self._original_qb = quiz.QUESTION_BANK
        quiz.QUESTION_BANK = list(SAMPLE_QUESTIONS)
        self._backup = None
        if os.path.exists(quiz.COLLECTIONS_FILE):
            with open(quiz.COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
                self._backup = f.read()
            os.remove(quiz.COLLECTIONS_FILE)

    def tearDown(self):
        quiz.QUESTION_BANK = self._original_qb
        if self._backup is not None:
            with open(quiz.COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
                f.write(self._backup)
        elif os.path.exists(quiz.COLLECTIONS_FILE):
            os.remove(quiz.COLLECTIONS_FILE)

    @patch('quiz.display_stats')
    @patch('quiz.run_quiz', return_value=(2, 2, []))
    def test_runs_quiz_with_collection_questions(self, mock_quiz, mock_stats):
        """Should run quiz with questions from the collection"""
        quiz.create_collection('my夹')
        quiz.add_to_collection('my夹', 1, 'single')
        quiz.add_to_collection('my夹', 2, 'single')
        quiz._run_collection_quiz('my夹', sequential=True)
        mock_quiz.assert_called_once()
        # Check that the questions passed to run_quiz are the right ones
        args, kwargs = mock_quiz.call_args
        questions = args[0]
        self.assertEqual(len(questions), 2)
        ids = [q['id'] for q in questions]
        self.assertIn(1, ids)
        self.assertIn(2, ids)
        # Should pass mode='sequential' and allow_collect=False
        self.assertEqual(kwargs['mode'], 'sequential')
        self.assertFalse(kwargs['allow_collect'])

    @patch('builtins.input', return_value='')
    @patch('os.system')
    @patch('builtins.print')
    def test_empty_collection_quiz(self, mock_print, mock_system, mock_input):
        """Should show message for empty collection"""
        quiz.create_collection('empty夹')
        quiz._run_collection_quiz('empty夹', sequential=True)
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('暂无题目', all_output)

    @patch('quiz.display_stats')
    @patch('quiz.run_quiz', return_value=(1, 1, []))
    def test_nonexistent_collection_does_nothing(self, mock_quiz, mock_stats):
        """Should do nothing for non-existent collection"""
        quiz._run_collection_quiz('no_such夹', sequential=True)
        mock_quiz.assert_not_called()
        mock_stats.assert_not_called()

    @patch('quiz.display_stats')
    @patch('quiz.run_quiz', return_value=(2, 2, []))
    @patch('random.shuffle')
    def test_random_mode_shuffles_before_quiz(self, mock_shuffle, mock_quiz, mock_stats):
        """Should shuffle questions when sequential=False"""
        quiz.create_collection('rand夹')
        quiz.add_to_collection('rand夹', 1, 'single')
        quiz.add_to_collection('rand夹', 2, 'single')
        quiz._run_collection_quiz('rand夹', sequential=False)
        mock_shuffle.assert_called_once()
        # Even in random mode, should pass mode='sequential' to run_quiz
        _, kwargs = mock_quiz.call_args
        self.assertEqual(kwargs['mode'], 'sequential')

    @patch('quiz.display_stats')
    @patch('quiz.run_quiz', return_value=(2, 1, [{'id': 1, 'type': 'single'}]))
    def test_displays_stats_after_quiz(self, mock_quiz, mock_stats):
        """Should call display_stats with quiz results"""
        quiz.create_collection('stat夹')
        quiz.add_to_collection('stat夹', 1, 'single')
        quiz.add_to_collection('stat夹', 2, 'single')
        quiz._run_collection_quiz('stat夹', sequential=True)
        mock_stats.assert_called_once_with(2, 1, 1)

    @patch('builtins.input', return_value='')
    @patch('os.system')
    @patch('builtins.print')
    def test_all_questions_deleted_shows_message(self, mock_print, mock_system, mock_input):
        """Should show message when all collection questions were deleted from bank"""
        quiz.create_collection('deleted夹')
        # Manually add a question reference with non-existent ID
        data = quiz.load_collections()
        data['collections']['deleted夹']['questions'] = [
            {'id': 999, 'type': 'single'}
        ]
        quiz.save_collections(data)
        quiz._run_collection_quiz('deleted夹', sequential=True)
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('已全部从题库删除', all_output)


class TestFindQuestion(unittest.TestCase):
    """Tests for _find_question()"""

    def setUp(self):
        self._original_qb = quiz.QUESTION_BANK
        quiz.QUESTION_BANK = list(SAMPLE_QUESTIONS)

    def tearDown(self):
        quiz.QUESTION_BANK = self._original_qb

    def test_find_existing_single(self):
        """Should find an existing single-choice question"""
        result = quiz._find_question(1, 'single')
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['type'], 'single')
        self.assertIn('毛泽东思想', result['question'])

    def test_find_existing_multi(self):
        """Should find an existing multi-choice question"""
        result = quiz._find_question(1, 'multi')
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['type'], 'multi')

    def test_find_nonexistent(self):
        """Should return None for non-existent question"""
        result = quiz._find_question(999, 'single')
        self.assertIsNone(result)

    def test_find_wrong_type(self):
        """Should return None when type doesn't match"""
        # ID 1 exists as both single and multi, but let's check a non-existent combo
        result = quiz._find_question(50, 'multi')
        self.assertIsNone(result)


class TestExportMarkdown(unittest.TestCase):
    """Tests for export to Markdown"""

    def setUp(self):
        self._original_qb = quiz.QUESTION_BANK
        quiz.QUESTION_BANK = list(SAMPLE_QUESTIONS)
        self._backup = None
        if os.path.exists(quiz.COLLECTIONS_FILE):
            with open(quiz.COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
                self._backup = f.read()
            os.remove(quiz.COLLECTIONS_FILE)

    def tearDown(self):
        quiz.QUESTION_BANK = self._original_qb
        if self._backup is not None:
            with open(quiz.COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
                f.write(self._backup)
        elif os.path.exists(quiz.COLLECTIONS_FILE):
            os.remove(quiz.COLLECTIONS_FILE)
        # Clean up exported files
        for f in os.listdir('.'):
            if f.startswith('test_export') and f.endswith('.md'):
                os.remove(f)

    @patch('builtins.input', return_value='test_export_result.md')
    def test_export_creates_file(self, mock_input):
        """Should create a Markdown file with collection questions"""
        quiz.create_collection('export夹')
        quiz.add_to_collection('export夹', 1, 'single')
        quiz.add_to_collection('export夹', 3, 'single')
        quiz._export_collection_markdown('export夹')
        self.assertTrue(os.path.exists('test_export_result.md'))
        with open('test_export_result.md', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('## 单选题', content)
        self.assertIn('**答案：', content)
        self.assertIn('**解析：**', content)

    @patch('builtins.input', return_value='test_export_result.md')
    def test_export_groups_by_type(self, mock_input):
        """Should group questions by single/multi type"""
        quiz.create_collection('export夹')
        quiz.add_to_collection('export夹', 1, 'single')
        quiz.add_to_collection('export夹', 1, 'multi')
        quiz._export_collection_markdown('export夹')
        with open('test_export_result.md', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('## 单选题', content)
        self.assertIn('## 多选题', content)

    @patch('builtins.input', return_value='test_export_result.md')
    def test_export_empty_collection(self, mock_input):
        """Should show message for empty collection"""
        quiz.create_collection('empty夹')
        quiz._export_collection_markdown('empty夹')
        # Should not create file for empty collection
        self.assertFalse(os.path.exists('test_export_result.md'))


class TestBankQuizIntegration(unittest.TestCase):
    """Tests for bank-specific quiz flow (Task 6)"""

    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()
        self.bank_path = self.tmpdir
        self.bank_name = '测试题库'
        self.sample_question = {
            'id': 1, 'type': 'single', 'question': '测试题',
            'options': {'A': '对', 'B': '错'}, 'answer': 'A', 'explanation': '解析'
        }

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if os.path.exists(quiz.WRONG_QUESTIONS_FILE):
            os.remove(quiz.WRONG_QUESTIONS_FILE)
        if os.path.exists(quiz.COLLECTIONS_FILE):
            os.remove(quiz.COLLECTIONS_FILE)

    def test_run_quiz_saves_wrong_to_bank(self):
        """答错时保存到题库的错题本"""
        questions = [self.sample_question]
        # answer, collect prompt (skip), enter to continue
        with patch('builtins.input', side_effect=['B', '', '']):
            quiz.run_quiz(questions, bank_path=self.bank_path, bank_name=self.bank_name)

        from bank_manager import load_bank_wrong_questions
        data = load_bank_wrong_questions(self.bank_path)
        self.assertIn('测试题库错题', data['wrong_books'])
        self.assertEqual(len(data['wrong_books']['测试题库错题']), 1)
        self.assertEqual(data['wrong_books']['测试题库错题'][0]['id'], 1)

    def test_run_quiz_correct_removes_from_bank_wrong(self):
        """答对时从题库错题本中移除"""
        from bank_manager import save_bank_wrong_question
        save_bank_wrong_question(self.bank_path, '测试题库错题', self.sample_question)

        questions = [self.sample_question]
        # answer, collect prompt (skip), enter to continue
        with patch('builtins.input', side_effect=['A', '', '']):
            quiz.run_quiz(questions, bank_path=self.bank_path, bank_name=self.bank_name)

        from bank_manager import load_bank_wrong_questions
        data = load_bank_wrong_questions(self.bank_path)
        self.assertEqual(len(data['wrong_books']['测试题库错题']), 0)

    def test_run_quiz_no_bank_uses_global(self):
        """无 bank_path 时使用全局错题本（向后兼容）"""
        questions = [self.sample_question]
        # answer, collect prompt (skip), enter to continue
        with patch('builtins.input', side_effect=['B', '', '']):
            quiz.run_quiz(questions)

        wrong = quiz.load_wrong_questions()
        found = any(q['id'] == 1 for q in wrong)
        self.assertTrue(found)

    def test_run_quiz_accepts_bank_params(self):
        """run_quiz 签名接受 bank_path 和 bank_name 参数"""
        import inspect
        sig = inspect.signature(quiz.run_quiz)
        self.assertIn('bank_path', sig.parameters)
        self.assertIn('bank_name', sig.parameters)

    def test_display_stats_shows_bank_name(self):
        """display_stats 显示题库名称"""
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            quiz.display_stats(10, 8, 2, '测试题库')
        output = f.getvalue()
        self.assertIn('测试题库', output)

    def test_display_stats_no_bank_name(self):
        """display_stats 无题库名时显示默认路径"""
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            quiz.display_stats(10, 8, 2)
        output = f.getvalue()
        self.assertIn('wrong_questions.json', output)


class TestLoadQuestionBank(unittest.TestCase):
    """Tests for load_question_bank() with banks/ folder"""

    def test_load_question_bank_from_banks_folder(self):
        """测试从 banks/ 文件夹加载题库"""
        import tempfile
        from bank_manager import scan_banks_folder
        with tempfile.TemporaryDirectory() as tmpdir:
            banks_dir = os.path.join(tmpdir, 'banks')
            bank_dir = os.path.join(banks_dir, '测试')
            os.makedirs(bank_dir)

            md_content = """## 单选题

**1. 测试（　）**

A. A
B. B
C. C
D. D

**答案：A**

**解析：** 测试

---
"""
            with open(os.path.join(bank_dir, 'test.md'), 'w', encoding='utf-8') as f:
                f.write(md_content)

            # Mock _scan_banks_folder to use our temp directory
            banks = scan_banks_folder(banks_dir)
            with patch('quiz._scan_banks_folder', return_value=banks):
                result = quiz.load_question_bank()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]['type'], 'single')

    @patch('quiz._scan_banks_folder', return_value=[])
    def test_load_question_bank_empty_banks(self, mock_scan):
        """banks/ 为空时返回空列表"""
        result = quiz.load_question_bank()
        self.assertEqual(result, [])

    @patch('quiz._scan_banks_folder', return_value=[
        {'name': 'test', 'path': '/tmp', 'questions': [{'id': 1, 'type': 'single'}]}
    ])
    def test_load_question_bank_returns_first_bank(self, mock_scan):
        """返回第一个题库的题目"""
        result = quiz.load_question_bank()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
