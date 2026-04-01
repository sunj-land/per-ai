import logging
import re
from bs4 import BeautifulSoup

try:
    import html2text
    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False

logger = logging.getLogger(__name__)

def html_to_markdown(html_content: str) -> str:
    """
    将 HTML 转换为 Markdown。如果存在不规范的标签属性（如包含反引号），会先进行清洗。
    如果未安装 html2text，则回退到提取纯文本。
    """
    if not html_content:
        return ""
    
    # 预处理：修复一些不规范的属性，例如 src=" `https://...` "
    html_content = re.sub(r'src=["\']\s*`?(https?://[^`"\']+)`?\s*["\']', r'src="\1"', html_content)
    html_content = re.sub(r'href=["\']\s*`?(https?://[^`"\']+)`?\s*["\']', r'href="\1"', html_content)

    if HAS_HTML2TEXT:
        try:
            h = html2text.HTML2Text()
            h.ignore_images = False
            h.ignore_links = False
            h.body_width = 0 # 避免自动换行导致 markdown 语法断裂
            return h.handle(html_content).strip()
        except Exception as e:
            logger.error(f"Error converting HTML to Markdown with html2text: {e}")
            # 回退到纯文本提取
            pass

    # 回退：使用 BeautifulSoup 提取纯文本
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {e}")
        return html_content

def clean_html_content(html_content: str) -> str:
    """
    清洗 HTML 内容，移除内联样式、危险标签和冗余属性。
    
    Args:
        html_content (str): 原始 HTML 内容。
        
    Returns:
        str: 清洗后的 HTML 内容。
    """
    if not html_content:
        return ""
        
    try:
        # 使用 html.parser 解析器
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 1. 移除危险标签及其内容
        dangerous_tags = [
            'script', 'iframe', 'object', 'embed', 'form', 
            'input', 'button', 'link', 'style', 'meta', 'head', 'title'
        ]
        for tag in soup.find_all(dangerous_tags):
            tag.decompose()
            
        # 2. 移除所有标签的 style, class, id 属性
        # 同时移除 on* 事件属性
        for tag in soup.find_all(True):
            # 移除指定属性
            attrs_to_remove = ['style', 'class', 'id', 'width', 'height'] # width/height 也常导致样式问题，建议移除让 CSS 控制
            for attr in attrs_to_remove:
                if tag.has_attr(attr):
                    del tag[attr]
            
            # 移除所有 on 开头的事件属性
            event_attrs = [key for key in tag.attrs.keys() if key.lower().startswith('on')]
            for attr in event_attrs:
                del tag[attr]

            # 对于 img 标签，保留 src, alt, title
            # 对于 a 标签，保留 href, target, title
            
        # 3. 清除空标签 (保留 img, br, hr)
        # 简单的空标签清理
        allowed_empty_tags = ['img', 'br', 'hr', 'source', 'track', 'area', 'col', 'param']
        
        # 查找所有空标签并移除
        # 注意：find_all 可能会包含嵌套的空标签，需要小心处理
        # 这里简单处理：如果标签没有文本且没有子标签（或者子标签也是空的），则移除
        # 实际上 BeautifulSoup 的 find_all 遍历顺序不保证层级关系，但通常是从上到下
        # 为了更彻底，可以递归清理，但这里做一层即可
        for tag in soup.find_all(True):
            if tag.name not in allowed_empty_tags:
                if not tag.get_text(strip=True) and not tag.contents:
                    tag.decompose()
                
        return str(soup)
        
    except Exception as e:
        logger.error(f"Error cleaning HTML content: {e}")
        # 如果出错，返回原始内容，避免数据丢失
        return html_content
