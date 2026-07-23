"""
代码编辑器模块单元测试

测试范围：
- get_language_from_extension 语言识别
- get_all_languages 返回所有支持语言
- tokenize_code 代码分词
- search_in_file 内容搜索（基础/大小写/正则/全词）
- replace_in_file 内容替换（基础/全部）
- get_file_outline 代码大纲
"""
import pytest
from unittest.mock import patch

from modules.code_editor import (
    get_language_from_extension,
    get_language_config,
    get_all_languages,
    tokenize_code,
    search_in_file,
    replace_in_file,
    get_file_outline,
    LANGUAGE_CONFIGS,
)


# ==================== get_language_from_extension ====================

class TestGetLanguageFromExtension:
    """语言识别测试"""

    @pytest.mark.unit
    @pytest.mark.parametrize('filename,expected', [
        ('script.js', 'javascript'),
        ('app.jsx', 'javascript'),
        ('module.mjs', 'javascript'),
        ('config.cjs', 'javascript'),
    ])
    def test_javascript_extensions(self, filename, expected):
        """javascript 相关扩展名识别"""
        assert get_language_from_extension(filename) == expected

    @pytest.mark.unit
    @pytest.mark.parametrize('filename,expected', [
        ('main.py', 'python'),
        ('gui.pyw', 'python'),
        ('types.pyi', 'python'),
    ])
    def test_python_extensions(self, filename, expected):
        """python 相关扩展名识别"""
        assert get_language_from_extension(filename) == expected

    @pytest.mark.unit
    @pytest.mark.parametrize('filename,expected', [
        ('Main.java', 'java'),
        ('index.html', 'html'),
        ('page.htm', 'html'),
        ('style.css', 'css'),
        ('style.scss', 'css'),
        ('style.sass', 'css'),
        ('style.less', 'css'),
        ('data.json', 'json'),
        ('data.jsonc', 'json'),
    ])
    def test_other_known_extensions(self, filename, expected):
        """其他已知扩展名识别"""
        assert get_language_from_extension(filename) == expected

    @pytest.mark.unit
    def test_unknown_extension_returns_plaintext(self):
        """未知扩展名应返回 plaintext"""
        assert get_language_from_extension('file.unknownext') == 'plaintext'
        assert get_language_from_extension('no_extension') == 'plaintext'
        assert get_language_from_extension('readme.xyz') == 'plaintext'

    @pytest.mark.unit
    def test_extension_case_insensitive(self):
        """扩展名应大小写不敏感"""
        assert get_language_from_extension('SCRIPT.JS') == 'javascript'
        assert get_language_from_extension('Main.PY') == 'python'

    @pytest.mark.unit
    def test_filename_with_path(self):
        """带路径的文件名应正确识别"""
        assert get_language_from_extension('/home/user/script.py') == 'python'
        assert get_language_from_extension('C:\\project\\app.js') == 'javascript'


# ==================== get_all_languages ====================

class TestGetAllLanguages:
    """get_all_languages 测试"""

    @pytest.mark.unit
    def test_returns_list(self):
        """应返回列表"""
        result = get_all_languages()
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.unit
    def test_each_language_has_required_fields(self):
        """每个语言项应包含 id/name/extensions 字段"""
        result = get_all_languages()
        for lang in result:
            assert 'id' in lang
            assert 'name' in lang
            assert 'extensions' in lang
            assert isinstance(lang['extensions'], list)
            assert len(lang['extensions']) > 0

    @pytest.mark.unit
    def test_includes_all_languages(self):
        """应包含 LANGUAGE_CONFIGS 中所有语言"""
        result = get_all_languages()
        ids = [lang['id'] for lang in result]
        for lang_id in LANGUAGE_CONFIGS:
            assert lang_id in ids

    @pytest.mark.unit
    def test_name_is_capitalized(self):
        """name 字段应为首字母大写"""
        result = get_all_languages()
        for lang in result:
            assert lang['name'] == lang['id'].capitalize()

    @pytest.mark.unit
    def test_includes_javascript_and_python(self):
        """应至少包含 javascript 和 python"""
        result = get_all_languages()
        ids = [lang['id'] for lang in result]
        assert 'javascript' in ids
        assert 'python' in ids


# ==================== tokenize_code ====================

class TestTokenizeCode:
    """tokenize_code 分词测试"""

    @pytest.mark.unit
    def test_returns_list(self):
        """应返回列表"""
        tokens = tokenize_code('x = 1', 'python')
        assert isinstance(tokens, list)

    @pytest.mark.unit
    def test_token_has_required_fields(self):
        """每个 token 应包含 type/value/start/end 字段"""
        tokens = tokenize_code('def foo():', 'python')
        assert len(tokens) > 0
        for tok in tokens:
            assert 'type' in tok
            assert 'value' in tok
            assert 'start' in tok
            assert 'end' in tok

    @pytest.mark.unit
    def test_python_keyword_recognized(self):
        """应识别 python 关键字"""
        tokens = tokenize_code('def foo():', 'python')
        keyword_tokens = [t for t in tokens if t['type'] == 'keyword']
        assert len(keyword_tokens) > 0
        assert keyword_tokens[0]['value'] == 'def'

    @pytest.mark.unit
    def test_javascript_keyword_recognized(self):
        """应识别 javascript 关键字"""
        tokens = tokenize_code('const x = 1;', 'javascript')
        keyword_tokens = [t for t in tokens if t['type'] == 'keyword']
        assert len(keyword_tokens) > 0
        assert keyword_tokens[0]['value'] == 'const'

    @pytest.mark.unit
    def test_string_token_recognized(self):
        """应识别字符串 token"""
        tokens = tokenize_code('x = "hello"', 'python')
        string_tokens = [t for t in tokens if t['type'] in
                         ('string_double', 'string_single', 'string_template')]
        assert len(string_tokens) > 0
        assert string_tokens[0]['value'] == '"hello"'

    @pytest.mark.unit
    def test_number_token_recognized(self):
        """应识别数字 token"""
        tokens = tokenize_code('x = 42', 'python')
        number_tokens = [t for t in tokens if t['type'] == 'number']
        assert len(number_tokens) > 0
        assert number_tokens[0]['value'] == '42'

    @pytest.mark.unit
    def test_comment_token_python(self):
        """应识别 python 注释"""
        tokens = tokenize_code('# a comment\nx = 1', 'python')
        comment_tokens = [t for t in tokens if t['type'] == 'comment_line']
        assert len(comment_tokens) > 0
        assert 'comment' in comment_tokens[0]['value'].lower()

    @pytest.mark.unit
    def test_empty_code_returns_empty_list(self):
        """空代码应返回空列表"""
        tokens = tokenize_code('', 'python')
        assert tokens == []

    @pytest.mark.unit
    def test_unknown_language_returns_tokens(self):
        """未知语言应仍能分词（使用默认空配置）"""
        tokens = tokenize_code('hello world', 'nonexistent')
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    @pytest.mark.unit
    def test_html_tokenize(self):
        """html 应使用 html 模式分词"""
        tokens = tokenize_code('<div class="x">text</div>', 'html')
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        # 应包含 tag_open 类型
        tag_tokens = [t for t in tokens if t['type'] == 'tag_open']
        assert len(tag_tokens) > 0


# ==================== search_in_file ====================

class TestSearchInFile:
    """search_in_file 内容搜索测试"""

    @pytest.mark.unit
    def test_basic_search_finds_match(self):
        """基础搜索应找到匹配项"""
        content = 'hello world\nfoo bar\nhello again'
        results = search_in_file(content, 'hello')
        assert isinstance(results, list)
        assert len(results) == 2  # 两处 hello
        # 第一处应位于第 1 行
        assert results[0]['line'] == 1
        assert results[0]['match'] == 'hello'

    @pytest.mark.unit
    def test_case_insensitive_default(self):
        """默认应大小写不敏感"""
        content = 'Hello HELLO hello'
        results = search_in_file(content, 'hello')
        assert len(results) == 3

    @pytest.mark.unit
    def test_case_sensitive_search(self):
        """启用大小写敏感时应仅匹配大小写相同的项"""
        content = 'Hello HELLO hello'
        results = search_in_file(content, 'Hello', case_sensitive=True)
        assert len(results) == 1
        assert results[0]['match'] == 'Hello'

    @pytest.mark.unit
    def test_regex_search(self):
        """正则表达式搜索"""
        content = 'foo123 bar456 baz789'
        results = search_in_file(content, r'\d+', regex=True)
        assert len(results) == 3
        # 验证匹配的值是数字
        for r in results:
            assert r['match'].isdigit()

    @pytest.mark.unit
    def test_whole_word_search(self):
        """全词匹配应只匹配完整单词"""
        content = 'cat category cat caterpillar cat'
        results = search_in_file(content, 'cat', whole_word=True)
        # 应匹配 3 处独立的 cat 单词（不匹配 category / caterpillar 中的 cat）
        assert len(results) == 3
        # 验证匹配到的都是独立的 cat 单词
        for r in results:
            assert r['match'] == 'cat'

    @pytest.mark.unit
    def test_search_returns_column_info(self):
        """搜索结果应包含列信息"""
        content = 'hello world'
        results = search_in_file(content, 'world')
        assert results[0]['column'] == 7  # world 起始于第 7 列（1-based）
        assert results[0]['end_column'] == 12

    @pytest.mark.unit
    def test_search_no_match_returns_empty_list(self):
        """未匹配时应返回空列表"""
        results = search_in_file('hello world', 'nonexistent')
        assert results == []

    @pytest.mark.unit
    def test_invalid_regex_returns_error(self):
        """无效正则应返回 error 字典"""
        result = search_in_file('hello', '[', regex=True)
        assert isinstance(result, dict)
        assert 'error' in result

    @pytest.mark.unit
    def test_multiline_content(self):
        """多行内容应分别返回每行的匹配"""
        content = 'foo\nbar\nfoo'
        results = search_in_file(content, 'foo')
        assert len(results) == 2
        assert results[0]['line'] == 1
        assert results[1]['line'] == 3


# ==================== replace_in_file ====================

class TestReplaceInFile:
    """replace_in_file 内容替换测试"""

    @pytest.mark.unit
    def test_basic_replace(self):
        """基础替换"""
        result = replace_in_file('hello world', 'world', 'python')
        assert result['content'] == 'hello python'
        assert result['replacements'] == 1

    @pytest.mark.unit
    def test_replace_all_occurrences(self):
        """应替换所有匹配项"""
        result = replace_in_file('foo foo foo', 'foo', 'bar')
        assert result['content'] == 'bar bar bar'
        assert result['replacements'] == 3

    @pytest.mark.unit
    def test_replace_case_insensitive(self):
        """大小写不敏感替换"""
        result = replace_in_file('Hello HELLO hello', 'hello', 'hi')
        assert result['replacements'] == 3

    @pytest.mark.unit
    def test_replace_case_sensitive(self):
        """大小写敏感替换"""
        result = replace_in_file('Hello HELLO hello', 'Hello', 'Hi', case_sensitive=True)
        assert result['replacements'] == 1
        assert 'Hi' in result['content']

    @pytest.mark.unit
    def test_replace_regex(self):
        """正则表达式替换"""
        result = replace_in_file('foo123 bar456', r'\d+', 'X', regex=True)
        assert result['replacements'] == 2
        assert result['content'] == 'fooX barX'

    @pytest.mark.unit
    def test_replace_whole_word(self):
        """全词替换"""
        result = replace_in_file('cat category cat', 'cat', 'dog', whole_word=True)
        assert result['replacements'] == 2
        assert 'category' in result['content']
        assert 'dog category dog' == result['content']

    @pytest.mark.unit
    def test_replace_no_match(self):
        """无匹配时 replacements 应为 0"""
        result = replace_in_file('hello world', 'nonexistent', 'X')
        assert result['content'] == 'hello world'
        assert result['replacements'] == 0

    @pytest.mark.unit
    def test_replace_invalid_regex_returns_error(self):
        """无效正则应返回 error 字典"""
        result = replace_in_file('hello', '[', 'X', regex=True)
        assert isinstance(result, dict)
        assert 'error' in result


# ==================== get_file_outline ====================

class TestGetFileOutline:
    """get_file_outline 代码大纲测试"""

    @pytest.mark.unit
    def test_python_outline_functions(self):
        """python 大纲应识别 def 函数"""
        content = 'def foo():\n    pass\n\ndef bar():\n    return 1'
        outline = get_file_outline(content, 'python')
        assert len(outline) == 2
        names = [item['name'] for item in outline]
        assert 'foo' in names
        assert 'bar' in names

    @pytest.mark.unit
    def test_python_outline_classes(self):
        """python 大纲应识别 class"""
        content = 'class MyClass:\n    pass\n\nclass Another:\n    pass'
        outline = get_file_outline(content, 'python')
        assert len(outline) == 2
        names = [item['name'] for item in outline]
        assert 'MyClass' in names
        assert 'Another' in names

    @pytest.mark.unit
    def test_python_outline_mixed(self):
        """python 大纲应同时识别函数和类"""
        content = 'class Foo:\n    def method(self):\n        pass\n\ndef func():\n    pass'
        outline = get_file_outline(content, 'python')
        # 应包含 class Foo, def method, def func
        types = [item['type'] for item in outline]
        assert 'class' in types
        assert 'function' in types

    @pytest.mark.unit
    def test_javascript_outline_functions(self):
        """javascript 大纲应识别 function"""
        content = 'function foo() {\n  return 1\n}\n\nfunction bar() {\n  return 2\n}'
        outline = get_file_outline(content, 'javascript')
        assert len(outline) >= 2
        names = [item['name'] for item in outline]
        assert 'foo' in names
        assert 'bar' in names

    @pytest.mark.unit
    def test_javascript_outline_arrow_functions(self):
        """javascript 大纲应识别箭头函数"""
        content = 'const add = (a, b) => a + b'
        outline = get_file_outline(content, 'javascript')
        assert len(outline) >= 1
        names = [item['name'] for item in outline]
        assert 'add' in names

    @pytest.mark.unit
    def test_javascript_outline_classes(self):
        """javascript 大纲应识别 class"""
        content = 'class MyClass {\n  constructor() {}\n}'
        outline = get_file_outline(content, 'javascript')
        assert len(outline) >= 1
        assert any(item['name'] == 'MyClass' for item in outline)

    @pytest.mark.unit
    def test_html_outline_sections(self):
        """html 大纲应识别标题/结构标签"""
        content = '<html><body><h1>Title</h1><nav>Menu</nav></body></html>'
        outline = get_file_outline(content, 'html')
        assert len(outline) >= 1

    @pytest.mark.unit
    def test_outline_returns_line_numbers(self):
        """大纲项应包含行号"""
        content = 'def foo():\n    pass\n\ndef bar():\n    return 1'
        outline = get_file_outline(content, 'python')
        for item in outline:
            assert 'line' in item
            assert isinstance(item['line'], int)
            assert item['line'] >= 1

    @pytest.mark.unit
    def test_outline_unsupported_language_returns_empty(self):
        """不支持的语言应返回空列表"""
        content = 'some content'
        outline = get_file_outline(content, 'rust')
        assert outline == []

    @pytest.mark.unit
    def test_outline_empty_content(self):
        """空内容应返回空列表"""
        outline = get_file_outline('', 'python')
        assert outline == []
