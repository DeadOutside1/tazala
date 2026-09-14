"""
Wrapped Service: calculates detox analytics, assigns archetypes,
and generates Spotify-style visual summary cards.
"""
import io
import logging

from PIL import Image, ImageDraw, ImageFont
from redis.asyncio import Redis

from app.cleaner.schemas import CleanResult
from app.scanner.schemas import ScanResult
from app.wrapped.schemas import WrappedStats, ZenArchetype

logger = logging.getLogger(__name__)

# Design System Colors
BG_COLOR = (13, 15, 23)          # #0D0F17 - Deep Graphite
CARD_BG = (24, 28, 42)           # #181C2A - Dark Surface
CARD_BORDER = (38, 45, 68)       # #262D44 - Card outline
NEON_MINT = (0, 245, 155)        # #00F59B - Primary Accent
CYBER_CYAN = (0, 229, 255)       # #00E5FF - Secondary Accent
SOFT_WHITE = (243, 244, 246)     # #F3F4F6 - Main Text
MUTED_GRAY = (156, 163, 175)     # #9CA3AF - Secondary Text


class WrappedService:
    """Computes detox stats and renders shareable Wrapped images."""

    @staticmethod
    def calculate_wrapped_stats(
        scan_result: ScanResult,
        clean_result: CleanResult | None = None,
        username: str | None = None,
    ) -> WrappedStats:
        """
        Calculate metrics, time saved, Zen Score, and determine behavioral archetype.
        """
        messages_cleared = (
            clean_result.messages_marked if clean_result else scan_result.total_unread
        )
        folders_count = len(clean_result.folders_created) if clean_result else 0
        dead_chats = scan_result.dead_count + scan_result.zombie_count

        # 15 seconds saved per cleared unread message
        time_saved_hours = round((messages_cleared * 15) / 3600, 1)

        # Zen Score: 100 minus penalties for unreads and dead chats
        unread_penalty = min(40, int((messages_cleared / 5000) * 40))
        dead_penalty = min(30, int((scan_result.dead_percentage / 100) * 30))
        zen_score = max(10, min(100, 100 - unread_penalty - dead_penalty))

        # Archetype determination
        if messages_cleared > 20000 or scan_result.dead_percentage > 60:
            archetype = ZenArchetype.DIGITAL_HOARDER
            title = "Цифровой плюшкин"
            description = "Копил каналы годами. Пришло время отпустить."
        elif messages_cleared > 5000 or scan_result.dead_percentage > 35:
            archetype = ZenArchetype.CHAOS_LORD
            title = "Повелитель хаоса"
            description = "Красный бейдж Telegram управлял твоей жизнью."
        elif messages_cleared > 500:
            archetype = ZenArchetype.INFO_COLLECTOR
            title = "Инфо-коллекционер"
            description = "Любишь читать, но лента победила."
        else:
            archetype = ZenArchetype.DIGITAL_MONK
            title = "Цифровой монах"
            description = "Абсолютный дзен и контроль над входящими."

        top_source = (
            scan_result.top_unread_chats[0].title
            if scan_result.top_unread_chats
            else None
        )

        return WrappedStats(
            session_id=scan_result.session_id,
            username=username,
            total_dialogs=scan_result.total_dialogs,
            messages_cleared=messages_cleared,
            dead_chats_count=dead_chats,
            folders_created_count=folders_count,
            time_saved_hours=time_saved_hours,
            zen_score=zen_score,
            archetype=archetype,
            archetype_title=title,
            archetype_description=description,
            top_unread_source=top_source,
        )

    @staticmethod
    def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Safe font loader with fallbacks across Windows, Linux, and Docker."""
        candidates = [
            "arialbd.ttf" if bold else "arial.ttf",
            "Arial.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "segoeui.ttf",
            "Helvetica.ttf",
        ]
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def generate_wrapped_card(self, stats: WrappedStats) -> bytes:
        """
        Generate high-resolution 1080x1350 vertical Spotify Wrapped-style card.
        """
        width, height = 1080, 1350
        image = Image.new("RGB", (width, height), BG_COLOR)
        draw = ImageDraw.Draw(image)

        # 1. Glowing decorative background accents
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        # Top-right Cyan glow
        overlay_draw.ellipse([700, -100, 1200, 400], fill=(0, 229, 255, 25))
        # Bottom-left Mint glow
        overlay_draw.ellipse([-150, 950, 450, 1550], fill=(0, 245, 155, 20))
        image.paste(Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB"))
        draw = ImageDraw.Draw(image)

        # 2. Header
        title_font = self._load_font(52, bold=True)
        sub_font = self._load_font(26, bold=False)
        user_font = self._load_font(28, bold=True)

        draw.text((80, 70), "TAZALA WRAPPED", fill=NEON_MINT, font=title_font)
        draw.text((80, 135), "ИТОГИ ИНФО-ДЕТОКСА", fill=MUTED_GRAY, font=sub_font)

        handle = f"@{stats.username}" if stats.username else "Личный отчет"
        draw.text((80, 185), handle, fill=SOFT_WHITE, font=user_font)

        # 3. Central Archetype Card
        card_box = [80, 260, 1000, 590]
        draw.rounded_rectangle(card_box, radius=28, fill=CARD_BG, outline=CARD_BORDER, width=2)

        arch_title_font = self._load_font(46, bold=True)
        arch_sub_font = self._load_font(26, bold=False)
        score_font = self._load_font(30, bold=True)

        badge_text = f"🧘 {stats.archetype_title.upper()}"
        draw.text((120, 295), badge_text, fill=NEON_MINT, font=arch_title_font)

        # Zen Score and Bar
        score_text = f"ZEN SCORE: {stats.zen_score} / 100"
        draw.text((120, 365), score_text, fill=CYBER_CYAN, font=score_font)

        # Progress bar
        bar_x, bar_y, bar_w, bar_h = 120, 420, 760, 18
        draw.rounded_rectangle(
            [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
            radius=9,
            fill=(38, 45, 68),
        )
        fill_w = int(bar_w * (stats.zen_score / 100))
        if fill_w > 0:
            draw.rounded_rectangle(
                [bar_x, bar_y, bar_x + fill_w, bar_y + bar_h],
                radius=9,
                fill=NEON_MINT,
            )

        # Description
        draw.text((120, 475), stats.archetype_description, fill=SOFT_WHITE, font=arch_sub_font)

        # 4. 2x2 Metric Tiles Grid
        tile_num_font = self._load_font(56, bold=True)
        tile_label_font = self._load_font(24, bold=False)

        tiles = [
            (
                [80, 640, 520, 890],
                f"{stats.messages_cleared:,}",
                "Непрочитанных обнулено",
                NEON_MINT,
            ),
            (
                [560, 640, 1000, 890],
                f"{stats.time_saved_hours} ч",
                "Времени сэкономлено",
                CYBER_CYAN,
            ),
            (
                [80, 930, 520, 1180],
                str(stats.dead_chats_count),
                "Мёртвых чатов в архиве",
                SOFT_WHITE,
            ),
            (
                [560, 930, 1000, 1180],
                str(stats.folders_created_count),
                "Смарт-папок создано",
                NEON_MINT,
            ),
        ]

        for box, num_str, label_str, color in tiles:
            draw.rounded_rectangle(box, radius=24, fill=CARD_BG, outline=CARD_BORDER, width=2)
            draw.text((box[0] + 35, box[1] + 45), num_str, fill=color, font=tile_num_font)
            draw.text(
                (box[0] + 35, box[1] + 140), label_str, fill=MUTED_GRAY, font=tile_label_font
            )

        # 5. Footer
        footer_font = self._load_font(26, bold=True)
        footer_text = "Очисти свой Telegram: @TazalaBot"
        draw.text((width // 2 - 220, 1240), footer_text, fill=CYBER_CYAN, font=footer_font)

        # Save to buffer
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    @staticmethod
    async def save_wrapped(redis: Redis, stats: WrappedStats, ttl: int = 86400) -> None:
        """Cache Wrapped stats in Redis for 24 hours."""
        key = f"wrapped:{stats.session_id}"
        await redis.setex(key, ttl, stats.model_dump_json())
        logger.info(
            "Wrapped stats for session %s saved to Redis (TTL %ds)",
            stats.session_id[:8],
            ttl,
        )

    @staticmethod
    async def get_cached_wrapped(redis: Redis, session_id: str) -> WrappedStats | None:
        """Retrieve cached Wrapped stats from Redis."""
        key = f"wrapped:{session_id}"
        raw = await redis.get(key)
        if not raw:
            return None
        data = raw.decode() if isinstance(raw, bytes) else raw
        return WrappedStats.model_validate_json(data)
