import re
from typing import List, Set
import logging

logger = logging.getLogger(__name__)

DEFAULT_SENSITIVE_WORDS = [
    "傻逼", "操你", "妈的", "他妈", "草泥马", "王八蛋",
    "去死", "滚蛋", "混蛋", "贱人", "婊子", "妓女",
    "赌博", "博彩", "六合彩", "时时彩", "私彩",
    "毒品", "冰毒", "海洛因", "大麻", "摇头丸",
    "代开发票", "办证", "信用卡套现", "贷款",
    "法轮功", "台独", "藏独", "疆独",
]


class SensitiveWordFilter:
    def __init__(self, custom_words: List[str] = None):
        self.sensitive_words: Set[str] = set(DEFAULT_SENSITIVE_WORDS)
        if custom_words:
            self.sensitive_words.update(custom_words)
        
        self._build_pattern()
    
    def _build_pattern(self):
        if not self.sensitive_words:
            self.pattern = None
            return
        
        escaped_words = [re.escape(word) for word in self.sensitive_words]
        self.pattern = re.compile('|'.join(escaped_words), re.IGNORECASE)
    
    def add_words(self, words: List[str]):
        self.sensitive_words.update(words)
        self._build_pattern()
    
    def remove_words(self, words: List[str]):
        for word in words:
            self.sensitive_words.discard(word)
        self._build_pattern()
    
    def contains_sensitive(self, text: str) -> bool:
        if not self.pattern or not text:
            return False
        return bool(self.pattern.search(text))
    
    def find_sensitive_words(self, text: str) -> List[str]:
        if not self.pattern or not text:
            return []
        
        found = []
        for match in self.pattern.finditer(text):
            found.append(match.group())
        return list(set(found))
    
    def filter_text(self, text: str, replacement: str = "***") -> str:
        if not self.pattern or not text:
            return text
        
        def replace_func(match):
            word = match.group()
            return replacement * len(word)
        
        return self.pattern.sub(replace_func, text)
    
    def check_and_filter(self, text: str) -> dict:
        if not text:
            return {
                "original": text,
                "filtered": text,
                "has_sensitive": False,
                "sensitive_words": [],
                "blocked": False
            }
        
        sensitive_words = self.find_sensitive_words(text)
        has_sensitive = len(sensitive_words) > 0
        
        blocked = False
        if has_sensitive:
            blocked_words = {"赌博", "毒品", "冰毒", "海洛因", "大麻", "摇头丸", 
                           "法轮功", "台独", "藏独", "疆独", "博彩", "六合彩"}
            if any(word in blocked_words for word in sensitive_words):
                blocked = True
        
        filtered_text = self.filter_text(text) if has_sensitive else text
        
        if has_sensitive:
            logger.warning(f"检测到敏感词: {sensitive_words}, 是否拦截: {blocked}")
        
        return {
            "original": text,
            "filtered": filtered_text,
            "has_sensitive": has_sensitive,
            "sensitive_words": sensitive_words,
            "blocked": blocked
        }


sensitive_filter = SensitiveWordFilter()
