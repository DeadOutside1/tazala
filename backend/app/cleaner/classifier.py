"""
Intelligent Chat Classifier for Telegram Smart Folders.
Provides regex whole-word matching, category confidence scoring,
and exclusive folder assignment (no duplicate chats across folders).
"""
import logging
import re

from app.cleaner.schemas import FolderRule
from app.scanner.schemas import ChatStatus, ChatType, DialogInfo

logger = logging.getLogger(__name__)


class SmartClassifier:
    """
    Intelligent classifier that categorizes dialogs into smart folders
    using regex word boundaries, specificity-weighted confidence scores,
    and mutually exclusive assignment.
    """

    SPECIFICITY_MULTIPLIERS: dict[str, float] = {
        "💰": 1.3,
        "📚": 1.2,
        "💼": 1.1,
        "📰": 1.0,
        "🎮": 1.0,
    }

    @staticmethod
    def match_keyword(text: str, keyword: str) -> bool:
        """
        Check if keyword matches within text using word boundaries.
        Supports both single words ('it', 'dev') and multi-word phrases ('machine learning').
        Prevents substring false positives (e.g. 'it' in 'bitcoin' or 'dev' in 'девушки').
        """
        if not text or not keyword:
            return False
        kw = keyword.strip()
        if not kw:
            return False

        pattern = rf"\b{re.escape(kw)}\b"
        if re.search(pattern, text, re.IGNORECASE):
            return True

        # Tech abbreviation expansion: 'dev' matches 'developer(s)' and 'development'
        if kw.lower() == "dev":
            dev_pattern = r"\bdev(elop(er|ment|ing)?)?s?\b"
            return bool(re.search(dev_pattern, text, re.IGNORECASE))

        return False

    @classmethod
    def get_specificity_multiplier(cls, rule: FolderRule) -> float:
        """
        Resolve category specificity multiplier for confidence scoring.
        Prioritizes narrow domains (Finance 1.3x, Study 1.2x, Work 1.1x)
        over broad feeds (News 1.0x, Memes 1.0x).
        """
        if rule.emoji and rule.emoji in cls.SPECIFICITY_MULTIPLIERS:
            return cls.SPECIFICITY_MULTIPLIERS[rule.emoji]

        title_lower = rule.title.lower()
        finance_kw = ("финанс", "finance", "крипт", "crypto", "деньг", "money")
        if any(w in title_lower for w in finance_kw):
            return 1.3
        if any(w in title_lower for w in ("обучен", "study", "educat", "курс", "course")):
            return 1.2
        if any(w in title_lower for w in ("работ", "work", "job", "it", "dev", "карьер")):
            return 1.1
        return 1.0

    @classmethod
    def score_dialog_for_rule(cls, dialog_title: str, rule: FolderRule) -> float:
        """
        Calculate confidence score of a dialog title for a given folder rule.
        - Matches single-word keywords: +1.0 base score.
        - Matches multi-word phrases: +2.0 base score (higher confidence).
        - Multiplies base score by category specificity multiplier.
        - Cutoff: score < 1.0 returns 0.0 (dialog does not qualify).
        """
        if not dialog_title or not rule.keywords:
            return 0.0

        base_score = 0.0
        for kw in rule.keywords:
            if cls.match_keyword(dialog_title, kw):
                if len(kw.strip().split()) >= 2:
                    base_score += 2.0
                else:
                    base_score += 1.0

        if base_score <= 0.0:
            return 0.0

        multiplier = cls.get_specificity_multiplier(rule)
        final_score = base_score * multiplier
        if final_score < 1.0:
            return 0.0
        return round(final_score, 2)

    @classmethod
    def classify_dialogs(
        cls,
        dialogs: list[DialogInfo],
        active_rules: list[FolderRule],
    ) -> dict[str, list[DialogInfo]]:
        """
        Exclusively assign dialogs into active folders (1 chat = strictly 1 folder).

        Phases:
        1. Dead / Zombie chats: strictly assigned to Inactive/Dead folder (emoji '🗑').
        2. Personal chats: user dialogs (type USER) strictly assigned to '💬 Личные'.
        3. Thematic feeds: remaining dialogs scored against thematic rules,
           assigned to highest score.
        """
        result: dict[str, list[DialogInfo]] = {rule.title: [] for rule in active_rules}
        assigned_chat_ids: set[int] = set()

        # Phase 1: Dead & Zombie chats
        dead_rule = next(
            (
                r for r in active_rules
                if r.emoji == "🗑"
                or any(w in r.title.lower() for w in ("мёртв", "dead", "inactive"))
            ),
            None,
        )
        if dead_rule:
            for d in dialogs:
                if (
                    d.id not in assigned_chat_ids
                    and d.status in (ChatStatus.DEAD, ChatStatus.ZOMBIE)
                ):
                    result[dead_rule.title].append(d)
                    assigned_chat_ids.add(d.id)

        # Phase 2: Personal user chats
        personal_rule = next(
            (
                r for r in active_rules
                if r.emoji == "💬" or any(w in r.title.lower() for w in ("личн", "personal"))
            ),
            None,
        )
        if personal_rule:
            for d in dialogs:
                if d.id not in assigned_chat_ids and d.type == ChatType.USER:
                    result[personal_rule.title].append(d)
                    assigned_chat_ids.add(d.id)

        # Phase 3: Thematic channels and groups
        thematic_rules = [
            r for r in active_rules
            if r != dead_rule and r != personal_rule
        ]

        for d in dialogs:
            if d.id in assigned_chat_ids:
                continue

            best_rule: FolderRule | None = None
            best_score: float = 0.0

            for rule in thematic_rules:
                if rule.categories and d.type not in rule.categories:
                    continue

                score = cls.score_dialog_for_rule(d.title, rule)
                if score > best_score:
                    best_score = score
                    best_rule = rule

            if best_rule and best_score >= 1.0:
                result[best_rule.title].append(d)
                assigned_chat_ids.add(d.id)

        total_assigned = len(assigned_chat_ids)
        logger.info(
            "Classified %d chats across %d folders without duplicates",
            total_assigned,
            len(result),
        )
        return result
