"""
telegram_notifier.py — Async Telegram notification with retry and rate limiting.

Sends alert messages (text + photo) to a configured Telegram chat.
Implements exponential backoff retry (3x) and per-chat rate limiting.
"""

import asyncio
import io
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Async Telegram Bot notifier with retry and rate limiting.

    Sends suspicious event alerts and periodic snapshots to a configured
    Telegram chat. Handles Telegram API rate limits gracefully.
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        retry_count: int = 3,
        retry_backoff_base: float = 1.0,
        rate_limit_interval: float = 3.0,
        send_timeout: int = 30,
    ):
        """
        Args:
            bot_token: Telegram Bot API token.
            chat_id: Target chat/channel ID.
            retry_count: Max retries on failure.
            retry_backoff_base: Base delay for exponential backoff (seconds).
            rate_limit_interval: Min seconds between messages.
            send_timeout: Timeout for API calls (seconds).
        """
        self.bot_token = bot_token
        self.chat_id = str(chat_id)
        self.retry_count = retry_count
        self.retry_backoff_base = retry_backoff_base
        self.rate_limit_interval = rate_limit_interval
        self.send_timeout = send_timeout
        self.public_url = os.environ.get("PUBLIC_URL", "").strip()

        # Rate limiting
        self._last_send_time: float = 0.0
        self._send_lock = asyncio.Lock()

        # Message queue for async sending
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False

        # Stats
        self._sent_count: int = 0
        self._error_count: int = 0

        # Bot instance (lazy init)
        self._bot = None
        self._enabled = bool(bot_token and chat_id
                            and bot_token != "your_bot_token_here"
                            and chat_id != "your_chat_id_here")

        if self._enabled:
            logger.info("TelegramNotifier initialized (chat_id=%s)", chat_id)
        else:
            logger.warning("TelegramNotifier disabled — missing bot_token or chat_id")

    async def initialize(self) -> None:
        """Initialize the Telegram bot instance."""
        if not self._enabled:
            return

        try:
            from telegram import Bot
            self._bot = Bot(token=self.bot_token)
            # Test connection
            me = await self._bot.get_me()
            logger.info("Telegram bot connected: @%s (%s)", me.username, me.first_name)
        except ImportError:
            logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
            self._enabled = False
        except Exception as e:
            logger.error("Failed to initialize Telegram bot: %s", e)
            self._enabled = False

    def stop(self) -> None:
        """Disable notifier to suppress any outgoing alerts or messages during/after shutdown."""
        self._enabled = False
        logger.info("TelegramNotifier stopped.")

    def _escape_md(self, text: str) -> str:
        """Escape special characters for Telegram MarkdownV2."""
        chars = r"_*[]()~`>#+-=|{}.!"
        for char in chars:
            text = text.replace(char, f"\\{char}")
        return text

    async def send_video(self, camera_name: str, event_id: str, video_path: str) -> bool:
        """Send a recorded video clip to Telegram.
        
        Args:
            camera_name: Camera name.
            event_id: Event UUID.
            video_path: Path to the video file.
            
        Returns:
            True if sent successfully.
        """
        if not self._enabled or self._bot is None:
            return False

        if not video_path or not Path(video_path).is_file():
            logger.error("Video file not found: %s", video_path)
            return False
            
        local_time_esc = self._escape_md(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        event_esc = self._escape_md(event_id[:8])
        
        caption = (
            f"🎥 *Critical Event Video*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📹 *Camera:* {self._escape_md(camera_name)}\n"
            f"🔖 *Event:* {event_esc}\n"
            f"🕐 *Time:* {local_time_esc}"
        )
        if self.public_url:
            caption += f"\n🔗 *Dashboard:* [Buka Link]({self.public_url})"
        
        return await self._do_send_video(caption, video_path)
        
    async def _do_send_video(self, caption: str, video_path: str) -> bool:
        """Internal coroutine to actually send the video with retries."""
        from telegram.constants import ParseMode
        from telegram.error import RetryAfter, TimedOut, NetworkError
        
        async with self._send_lock:
            for attempt in range(self.retry_count):
                try:
                    await self._wait_rate_limit()

                    with open(video_path, 'rb') as video_file:
                        await self._bot.send_video(
                            chat_id=self.chat_id,
                            video=video_file,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN_V2,
                            read_timeout=60,
                            write_timeout=60,
                            connect_timeout=self.send_timeout,
                        )
                    
                    self._last_send_time = time.time()
                    self._sent_count += 1
                    logger.info("Telegram video sent successfully (attempt %d)", attempt + 1)
                    return True

                except RetryAfter as e:
                    wait_time = e.retry_after + 1.0
                    logger.warning("Telegram rate limit hit. Waiting %.1fs", wait_time)
                    await asyncio.sleep(wait_time)
                    
                except (TimedOut, NetworkError) as e:
                    backoff = self.retry_backoff_base * (2 ** attempt)
                    logger.warning("Telegram network error (attempt %d/%d): %s. Retrying in %.1fs", 
                                   attempt + 1, self.retry_count, e, backoff)
                    await asyncio.sleep(backoff)
                    
                except Exception as e:
                    logger.error("Failed to send Telegram video: %s", e)
                    break

        self._error_count += 1
        return False

    def format_mobile_link_message(self, public_url: str) -> str:
        """Format an announcement message containing the mobile dashboard access link."""
        local_time_esc = self._escape_md(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        url_esc = self._escape_md(public_url)
        return (
            f"📱 *CCTV Mobile Dashboard Online*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 *Time:* {local_time_esc}\n"
            f"🌐 *Public Link:* [Buka Dashboard]({public_url})\n"
            f"🔗 *URL:* `{url_esc}`\n\n"
            f"💡 *Akses HP:* Klik tautan di atas untuk memantau kamera CCTV langsung dari ponsel Anda\\."
        )

    async def send_mobile_link(self, public_url: str) -> bool:
        """Send mobile access link directly to Telegram."""
        if not self._enabled or self._bot is None:
            return False

        message = self.format_mobile_link_message(public_url)
        from telegram.constants import ParseMode

        async with self._send_lock:
            try:
                await self._wait_rate_limit()
                await self._bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=False,
                )
                logger.info("Mobile access link successfully sent to Telegram: %s", public_url)
                return True
            except Exception as e:
                logger.error("Failed to send mobile access link to Telegram: %s", e)
                return False

    def format_alert_caption(
        self,
        camera_name: str,
        score: float,
        triggered_rules: List[str],
        track_ids: List[int],
        event_id: str = "",
        alert_level: str = "SUSPICIOUS",
        posture: Optional[str] = None,
        vehicle_info: Optional[str] = None,
    ) -> str:
        """Format MarkdownV2 alert caption for Telegram notifications."""
        local_time_esc = self._escape_md(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        rules_str = ", ".join(triggered_rules) if triggered_rules else "N/A"
        tracks_str = str(list(track_ids)) if track_ids else "[]"
        score_esc = self._escape_md(f"{score:.0f}/100")
        event_esc = self._escape_md(event_id[:8]) if event_id else "N/A"

        if "fall_detected" in triggered_rules or (posture and "FALL" in posture.upper()):
            title = "🚨 *[FALL DETECTED / DARURAT]*"
        elif alert_level.upper() == "CRITICAL":
            title = "🚨 *CRITICAL DETECTED*"
        else:
            title = "⚠️ *SUSPICIOUS DETECTED*"

        caption = (
            f"{title}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📹 *Camera:* {self._escape_md(camera_name)}\n"
            f"🕐 *Time:* {local_time_esc}\n"
            f"⚠️ *Score:* {score_esc}\n"
            f"🔍 *Triggers:* {self._escape_md(rules_str)}\n"
            f"👤 *Track IDs:* {self._escape_md(tracks_str)}\n"
            f"🔖 *Event:* {event_esc}"
        )
        if posture:
            caption += f"\n🧍 *Postur:* {self._escape_md(posture)}"

        if vehicle_info:
            caption += f"\n🚗 *Vehicle:* {self._escape_md(vehicle_info)}"

        if self.public_url:
            caption += f"\n🔗 *Dashboard:* [Buka Link]({self.public_url})"

        return caption

    async def send_alert(
        self,
        camera_name: str,
        score: float,
        triggered_rules: List[str],
        track_ids: List[int],
        snapshot_path: Optional[str] = None,
        face_snapshot_path: Optional[str] = None,
        event_id: str = "",
        alert_level: str = "SUSPICIOUS",
        posture: Optional[str] = None,
        vehicle_info: Optional[str] = None,
    ) -> bool:
        """Send a suspicious activity alert with optional snapshot photo or photo album."""
        if not self._enabled or self._bot is None:
            logger.debug("Telegram disabled — alert not sent")
            return False

        caption = self.format_alert_caption(
            camera_name=camera_name,
            score=score,
            triggered_rules=triggered_rules,
            track_ids=track_ids,
            event_id=event_id,
            alert_level=alert_level,
            posture=posture,
            vehicle_info=vehicle_info,
        )

        if snapshot_path and face_snapshot_path and Path(snapshot_path).exists() and Path(face_snapshot_path).exists():
            return await self._send_media_group_photos([snapshot_path, face_snapshot_path], caption)
        else:
            return await self._send_message_with_photo(caption, snapshot_path)

    async def send_periodic_snapshot(
        self,
        camera_name: str,
        event_id: str,
        score: float,
        snapshot_path: Optional[str] = None,
        snapshot_number: int = 0,
    ) -> bool:
        """Send a periodic snapshot during an active event.

        Args:
            camera_name: Camera name.
            event_id: Active event ID.
            score: Current suspicion score.
            snapshot_path: Path to snapshot file.
            snapshot_number: Sequential snapshot number.

        Returns:
            True if sent successfully.
        """
        if not self._enabled or self._bot is None:
            return False

        local_time_esc = self._escape_md(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        score_esc = self._escape_md(f"{score:.0f}/100")
        event_esc = self._escape_md(event_id[:8])

        caption = (
            f"📸 *Periodic Snapshot* \\#{snapshot_number}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📹 *Camera:* {self._escape_md(camera_name)}\n"
            f"🔖 *Event:* {event_esc}\n"
            f"🕐 *Time:* {local_time_esc}\n"
            f"⚠️ *Score:* {score_esc}"
        )
        if self.public_url:
            caption += f"\n🔗 *Dashboard:* [Buka Link]({self.public_url})"

        return await self._send_message_with_photo(caption, snapshot_path)

    async def send_event_resolved(
        self,
        camera_name: str,
        event_id: str,
        duration_sec: float,
        total_snapshots: int,
    ) -> bool:
        """Send event resolution notification.

        Args:
            camera_name: Camera name.
            event_id: Resolved event ID.
            duration_sec: Total event duration in seconds.
            total_snapshots: Number of snapshots captured.

        Returns:
            True if sent successfully.
        """
        if not self._enabled or self._bot is None:
            return False

        local_time_esc = self._escape_md(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        duration_min = duration_sec / 60

        text = (
            f"✅ *Event Resolved*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📹 *Camera:* {self._escape_md(camera_name)}\n"
            f"🔖 *Event:* {event_id[:8]}\n"
            f"🕐 *Resolved at:* {local_time_esc}\n"
            f"⏱️ *Duration:* {duration_min:.1f} minutes\n"
            f"📸 *Snapshots:* {total_snapshots}"
        )
        if self.public_url:
            text += f"\n🔗 *Dashboard:* [Buka Link]({self.public_url})"

        return await self._send_text(text)

    async def send_health_alert(
        self,
        camera_name: str,
        status: str,
        message: str
    ) -> bool:
        """Send a health status alert (e.g., camera offline/online).

        Args:
            camera_name: Camera name.
            status: Health status ("OFFLINE", "ONLINE", or "WARNING").
            message: Descriptive message.

        Returns:
            True if sent successfully.
        """
        if not self._enabled or self._bot is None:
            return False

        local_time_esc = self._escape_md(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        status_upper = status.upper()
        if status_upper == "OFFLINE":
            icon = "⚠️"
            title = "*CAMERA OFFLINE*"
        elif status_upper == "ONLINE":
            icon = "✅"
            title = "*CAMERA ONLINE*"
        else:
            icon = "ℹ️"
            title = f"*{self._escape_md(status_upper)}*"

        text = (
            f"{icon} {title}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📹 *Camera:* {self._escape_md(camera_name)}\n"
            f"🕐 *Time:* {local_time_esc}\n"
            f"💬 *Status:* {self._escape_md(message)}"
        )
        if self.public_url:
            text += f"\n🔗 *Dashboard:* [Buka Link]({self.public_url})"

        return await self._send_text(text)

    async def send_reid_alert(
        self,
        global_person_id: str,
        prev_camera_name: str,
        current_camera_name: str,
        similarity: float,
        seconds_since_last: float,
    ) -> bool:
        """Send a Person Re-ID cross-camera notification.

        Args:
            global_person_id: Global person ID (e.g., 'P-0042').
            prev_camera_name: Camera where the person was last seen.
            current_camera_name: Camera where the person is now detected.
            similarity: Cosine similarity score (0-1).
            seconds_since_last: Seconds since last seen on the previous camera.

        Returns:
            True if sent successfully.
        """
        if not self._enabled or self._bot is None:
            return False

        local_time_esc = self._escape_md(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Format time since last seen
        if seconds_since_last >= 3600:
            time_ago = f"{seconds_since_last / 3600:.1f} jam lalu"
        elif seconds_since_last >= 60:
            time_ago = f"{int(seconds_since_last / 60)} menit lalu"
        else:
            time_ago = f"{int(seconds_since_last)} detik lalu"

        text = (
            f"🔄 *PERSON RE\\-IDENTIFIED*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Person ID:* {self._escape_md(global_person_id)}\n"
            f"📹 *Terakhir:* {self._escape_md(prev_camera_name)} \\({self._escape_md(time_ago)}\\)\n"
            f"📹 *Sekarang:* {self._escape_md(current_camera_name)}\n"
            f"🎯 *Similarity:* {self._escape_md(f'{similarity:.0%}')}\n"
            f"🕐 *Time:* {local_time_esc}"
        )
        if self.public_url:
            text += f"\n🔗 *Dashboard:* [Buka Link]({self.public_url})"

        return await self._send_text(text)

    # ----- Internal send methods -----

    async def _send_message_with_photo(
        self, caption: str, photo_path: Optional[str]
    ) -> bool:
        """Send a photo with caption, falling back to text-only if no photo."""
        if photo_path and Path(photo_path).exists():
            return await self._send_photo(photo_path, caption)
        else:
            return await self._send_text(caption)

    async def _send_media_group_photos(self, photo_paths: List[str], caption: str) -> bool:
        """Send multiple photos as an album (Media Group) with retry and rate limiting."""
        async with self._send_lock:
            await self._wait_rate_limit()

            for attempt in range(1, self.retry_count + 1):
                try:
                    from telegram import InputMediaPhoto
                    media = []
                    for i, p in enumerate(photo_paths):
                        with open(p, "rb") as f:
                            p_bytes = f.read()
                        if i == 0:
                            media.append(InputMediaPhoto(media=p_bytes, caption=caption, parse_mode="MarkdownV2"))
                        else:
                            media.append(InputMediaPhoto(media=p_bytes))

                    await self._bot.send_media_group(
                        chat_id=self.chat_id,
                        media=media,
                        read_timeout=self.send_timeout,
                        write_timeout=self.send_timeout,
                    )

                    self._last_send_time = time.time()
                    self._sent_count += 1
                    logger.info("Telegram media group album sent (attempt %d, %d photos)", attempt, len(media))
                    return True

                except Exception as e:
                    error_name = type(e).__name__
                    if "RetryAfter" in error_name or "Flood" in str(e):
                        retry_after = getattr(e, 'retry_after', 10)
                        logger.warning("Telegram rate limited, waiting %ds...", retry_after)
                        await asyncio.sleep(retry_after)
                        continue

                    if attempt < self.retry_count:
                        delay = self.retry_backoff_base * (2 ** (attempt - 1))
                        logger.warning(
                            "Telegram media group failed (attempt %d/%d): %s. Retrying in %.1fs...",
                            attempt, self.retry_count, e, delay
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error("Failed to send Telegram media group, will fallback to single photo: %s", e)
                        break

        # Outside lock: fallback to sending single primary photo
        logger.info("Falling back to sending single primary photo")
        return await self._send_photo(photo_paths[0], caption)

    async def _send_photo(self, photo_path: str, caption: str) -> bool:
        """Send a photo via Telegram with retry and rate limiting."""
        async with self._send_lock:
            await self._wait_rate_limit()

            for attempt in range(1, self.retry_count + 1):
                try:
                    with open(photo_path, "rb") as f:
                        photo_bytes = f.read()

                    await self._bot.send_photo(
                        chat_id=self.chat_id,
                        photo=photo_bytes,
                        caption=caption,
                        parse_mode="MarkdownV2",
                        read_timeout=self.send_timeout,
                        write_timeout=self.send_timeout,
                    )

                    self._last_send_time = time.time()
                    self._sent_count += 1
                    logger.info("Telegram photo sent (attempt %d)", attempt)
                    return True

                except Exception as e:
                    error_name = type(e).__name__

                    # Handle Telegram rate limit
                    if "RetryAfter" in error_name or "Flood" in str(e):
                        retry_after = getattr(e, 'retry_after', 10)
                        logger.warning(
                            "Telegram rate limited, waiting %ds...", retry_after
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    # Retry with exponential backoff
                    if attempt < self.retry_count:
                        delay = self.retry_backoff_base * (2 ** (attempt - 1))
                        logger.warning(
                            "Telegram send failed (attempt %d/%d): %s. Retrying in %.1fs...",
                            attempt,
                            self.retry_count,
                            e,
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "Telegram send failed after %d attempts: %s",
                            self.retry_count,
                            e,
                        )
                        self._error_count += 1

            # Try sending as text only (fallback if photo fails)
            logger.info("Falling back to text-only message")
            return await self._send_text(caption + "\n\n_\\(photo failed to send\\)_")

    async def _send_text(self, text: str) -> bool:
        """Send a text-only message via Telegram."""
        if not self._enabled or self._bot is None:
            return False

        async with self._send_lock:
            await self._wait_rate_limit()

            for attempt in range(1, self.retry_count + 1):
                try:
                    await self._bot.send_message(
                        chat_id=self.chat_id,
                        text=text,
                        parse_mode="MarkdownV2",
                        read_timeout=self.send_timeout,
                        write_timeout=self.send_timeout,
                    )

                    self._last_send_time = time.time()
                    self._sent_count += 1
                    logger.debug("Telegram text sent (attempt %d)", attempt)
                    return True

                except Exception as e:
                    if "RetryAfter" in type(e).__name__:
                        retry_after = getattr(e, 'retry_after', 10)
                        await asyncio.sleep(retry_after)
                        continue

                    if attempt < self.retry_count:
                        delay = self.retry_backoff_base * (2 ** (attempt - 1))
                        logger.warning(
                            "Telegram text send failed (attempt %d/%d): %s",
                            attempt,
                            self.retry_count,
                            e,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error("Telegram text send failed: %s", e)
                        self._error_count += 1

        return False

    async def _wait_rate_limit(self) -> None:
        """Wait if needed to respect per-chat rate limit."""
        elapsed = time.time() - self._last_send_time
        if elapsed < self.rate_limit_interval:
            wait = self.rate_limit_interval - elapsed
            logger.debug("Rate limit: waiting %.1fs", wait)
            await asyncio.sleep(wait)

    @staticmethod
    def _escape_md(text: str) -> str:
        """Escape special characters for Telegram MarkdownV2.

        Characters that need escaping: _ * [ ] ( ) ~ ` > # + - = | { } . !
        """
        special_chars = r"_*[]()~`>#+-=|{}.!"
        escaped = ""
        for char in text:
            if char in special_chars:
                escaped += f"\\{char}"
            else:
                escaped += char
        return escaped

    def get_stats(self) -> dict:
        """Get notification statistics."""
        return {
            "enabled": self._enabled,
            "sent_count": self._sent_count,
            "error_count": self._error_count,
        }
