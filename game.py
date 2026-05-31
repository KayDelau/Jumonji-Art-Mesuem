import sys
import time
import pygame

from settings import WIDTH, HEIGHT, FPS
from core.utils import get_font
from systems.hallway import Hallway
from systems.inventory import Inventory
from ui.renderer import Renderer
from systems.story_manager import StoryManager
from systems.mutation_manager import MutationManager
from systems.dialogue_manager import DialogueManager
from systems.puzzle_manager import PuzzleManager


class MidnightMuseumGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_caption("十文字美術館")



        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_title = get_font(34)
        self.font_menu_title = get_font(72)
        self.font_big = get_font(42)
        self.font_mid = get_font(24)
        self.font_small = get_font(20)
        self.font_tiny = get_font(16)

        self.running = True
        self.true_exit_found = False

        # 主選單頁面：main / options
        self.menu_page = "main"

        # 音效音量
        self.sfx_volume_ratio = 1.0

        # ==================================================
        # 暫停選單
        # ==================================================
        self.pause_menu_open = False

        # 背景音樂音量
        self.bgm_max_volume = 0.18
        self.bgm_volume_ratio = 1.0

        # 畫面亮度：
        # 1.0 = 最亮，不額外壓暗
        # 0.0 = 最暗
        self.screen_brightness = 1.0

        # 滑桿拖曳狀態
        self.dragging_bgm_slider = False
        self.dragging_brightness_slider = False


        # menu：主選單
        # hallway：橫向移動探索
        # observation：第一人稱觀察房間
        # item_preview：一般道具取得預覽畫面
        # fragment_preview：unlock 碎片取得預覽畫面
        # dialogue：NPC 對話畫面
        self.mode = "menu"

        # ==================================================
        # 遊戲時間系統
        # ==================================================
        self.real_start_time = time.time()
        self.game_minutes = 23 * 60 + 47

        self.time_paused = False
        self.pause_started_at = None
        self.total_paused_duration = 0

        # ==================================================
        # 基礎系統
        # ==================================================
        self.hallway = Hallway()
        self.inventory = Inventory()
        self.story = StoryManager()
        self.mutation = MutationManager()
        self.dialogue = DialogueManager()
        self.puzzle = PuzzleManager()

        self.register_dialogues()
        self.register_puzzles()

        # ==================================================
        # 背景音樂
        # ==================================================
        self.bgm_path = "BGM.mp3"
        self.bgm_loaded = False
        
        self.mutation_bgm_path = "mutate.mp3"
        self.using_mutation_bgm = False

        try:
            pygame.mixer.music.load(self.bgm_path)
            pygame.mixer.music.set_volume(self.bgm_max_volume * self.bgm_volume_ratio)
            self.bgm_loaded = True
        except pygame.error:
            print("[警告] 無法載入 BGM.mp3")

        # ==================================================
        # 音效
        # ==================================================
        self.open_door_sound = None
        self.lock_sound = None
        self.walk_sound = None
        self.walk_sound_channel = None

        try:
            self.open_door_sound = pygame.mixer.Sound("open_door.mp3")
            self.open_door_sound.set_volume(0.35)
        except pygame.error:
            print("[警告] 無法載入 open_door.mp3")

        try:
            self.walk_sound = pygame.mixer.Sound("walk.mp3")
            self.walk_sound.set_volume(1.0)
        except pygame.error:
            print("[警告] 無法載入 walk.mp3")

        try:
            self.lock_sound = pygame.mixer.Sound("lock.mp3")
            self.lock_sound.set_volume(0.28)
        except pygame.error:
            print("[警告] 無法載入 lock.mp3")

        # ==================================================
        # 口袋
        # ==================================================
        self.pocket_open = False
        # 口袋中目前正在查看資訊的道具
        self.pocket_inspected_item_id = None

        # 已按下【使用】，準備拿去和場景互動的道具
        self.active_item_id = None

        # 口袋左側清單滾動狀態
        self.pocket_scroll_index = 0
        self.pocket_visible_count = 4

        # ==================================================
        # 系統訊息：5 秒消失
        # ==================================================
        self.system_message = ""
        self.system_message_start_time = 0
        self.system_message_duration = 5

        # ==================================================
        # 劇情／對話訊息讀取狀態
        # ==================================================
        self.message_reading = False
        self.story_messages = []
        self.story_message_index = 0
        self.current_story_message = ""

        self.control_hint_pending = False
        self.control_hint_expire_time = 0

        # ==================================================
        # 觀察狀態
        # ==================================================
        self.observation_scene_id = None
        self.observation_location_name = ""
        self.observation_return_mode = "hallway"

        self.observation_return_area_id = "hall_main"
        self.observation_return_spawn_x = None
        self.observation_return_scene_id = None
        self.observation_return_location_name = ""

        # ==================================================
        # 道具預覽狀態
        # ==================================================
        self.preview_item_id = None
        self.preview_return_mode = "observation"
        self.preview_return_scene_id = None
        self.preview_return_location_name = ""
        # ==================================================
        # NPC 對話狀態
        # ==================================================
        self.dialogue_return_mode = "observation"        
        # ==================================================
        # unlock 碎片預覽狀態
        # ==================================================
        self.preview_fragment_id = None
        self.preview_fragment_title = ""
        self.preview_fragment_description = ""

        self.fragment_preview_return_mode = "hallway"
        self.fragment_preview_return_scene_id = None
        self.fragment_preview_return_location_name = ""

        # ==================================================
        # 房間狀態
        # locked：目前是否上鎖
        # unlock_condition：未來可填入解鎖條件
        # ==================================================
        self.room_states = {}
        self.reset_room_states()

        # ==================================================
        # 畫面震動效果
        # 用於表現門被鎖住、推門失敗
        # ==================================================
        self.screen_shake_active = False
        self.screen_shake_start_time = 0
        self.screen_shake_step_duration = 0.045

        self.screen_shake_offsets = [
            (-12, 0),
            (12, 0),
            (-10, 0),
            (10, 0),
            (-7, 0),
            (7, 0),
            (0, 0),
        ]

        # ==================================================
        # 可拾取互動道具
        # ==================================================
        self.collectible_items = {}
        self.reset_collectible_items()

        # ==================================================
        # 打字機效果
        # ==================================================
        self.typewriter_speed = 0.035

        self.typewriter_slots = {
            "bottom_main": self.create_empty_typewriter_slot(),
            "bottom_sub": self.create_empty_typewriter_slot(),
        }

        self.renderer = Renderer(self)

    # =========================================================
    # 遊戲重置
    # =========================================================
    def reset_game(self):
        self.mode = "hallway"
        self.true_exit_found = False
        self.pending_return_to_menu_after_messages = False

        self.real_start_time = time.time()
        self.game_minutes = 23 * 60 + 47

        self.time_paused = False
        self.pause_started_at = None
        self.total_paused_duration = 0

        self.pause_menu_open = False
        self.dragging_bgm_slider = False
        self.dragging_brightness_slider = False
        

        self.hallway.reset()
        self.inventory.reset()
        self.story.reset()
        self.mutation.reset()

        self.dialogue.reset()
        self.puzzle.reset()
        self.reset_room_states()
        self.reset_collectible_items()


        self.pocket_open = False
        self.pocket_inspected_item_id = None
        self.active_item_id = None
        self.pocket_scroll_index = 0

        self.system_message = ""
        self.system_message_start_time = 0

        self.control_hint_pending = True
        self.control_hint_expire_time = 0

        self.observation_scene_id = None
        self.observation_location_name = ""
        self.observation_return_mode = "hallway"

        self.observation_return_area_id = "hall_main"
        self.observation_return_spawn_x = None
        self.observation_return_scene_id = None
        self.observation_return_location_name = ""

        self.preview_item_id = None
        self.preview_return_mode = "observation"
        self.preview_return_scene_id = None
        self.preview_return_location_name = ""

        self.dialogue_return_mode = "observation"

        self.preview_fragment_id = None
        self.preview_fragment_title = ""
        self.preview_fragment_description = ""

        self.fragment_preview_return_mode = "hallway"
        self.fragment_preview_return_scene_id = None
        self.fragment_preview_return_location_name = ""

        self.screen_shake_active = False
        self.screen_shake_start_time = 0

        self.reset_all_typewriters()
        self.stop_walk_sound()

        self.using_mutation_bgm = False

        # 開始遊戲後播放 BGM
        if self.bgm_loaded:
            try:
                pygame.mixer.music.load(self.bgm_path)
                pygame.mixer.music.set_volume(
                    self.bgm_max_volume * self.bgm_volume_ratio
                )
                pygame.mixer.music.play(-1)
            except pygame.error:
                print("[警告] 無法播放 BGM.mp3")

        self.start_message_reading([
            "你揉著後腦袋醒來，美術館已經空無一人。",
            "窗外也已入夜。",
            "你試圖打開大門。",
            "「喀嚓。」",
            "卻發現門被人從外側鎖上，只能在館內尋找其他出口。"
        ])

    # =========================================================
    # 對話資料註冊
    # =========================================================
    def register_dialogues(self):
        """
        先放一段測試對話。
        Step 5 會改成正式的小女孩初遇對話。
        """
        self.dialogue.register_dialogue(
            "test_dialogue",
            {
                "start": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "你聽得見我說話嗎？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "這只是目前用來測試的對話。",
                    "next": "choice"
                },
                "choice": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "你想回答什麼？",
                    "choices": [
                        {
                            "text": "我聽得見。",
                            "next": "reply_yes"
                        },
                        {
                            "text": "你是誰？",
                            "next": "reply_who"
                        }
                    ]
                },
                "reply_yes": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "那就好。",
                    "next": None
                },
                "reply_who": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "現在還不能告訴你。",
                    "next": None
                }
            }
        )
        self.dialogue.register_dialogue(
            "girl_girls_room_intro",
            {
                "start": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "……你是來找我的嗎？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "不對，你看起來也被困在這裡了。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "既然你能打開那扇門，也許你可以試著回答我的問題。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "聽好了……如果找不到真正被藏起來的東西，你就會和我一樣，永遠留在這裡。",
                    "action": "start_girl_riddle_1"
                }
            }
        )
        self.dialogue.register_dialogue(
            "girl_history_room_intro",
            {
                "start": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "你真的走出來了。",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "可是只有你一個人，是離不開這裡的。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "館裡還有其他人。也許你可以問問他們。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "但在那之前，你要先回答我第二個問題。",
                    "action": "start_girl_riddle_2"
                }
            }
        )
        self.dialogue.register_dialogue(
            "worker_sculpture_intro",
            {
                "start": {
                    "speaker": "工友",
                    "speaker_side": "right",
                    "portrait": "worker",
                    "text": "欸？你是新來的？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "工友",
                    "speaker_side": "right",
                    "portrait": "worker",
                    "text": "館長終於找人來修那些東西了啊。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "工友",
                    "speaker_side": "right",
                    "portrait": "worker",
                    "text": "不過我得先問你一題，免得你把東西越修越壞。",
                    "action": "start_worker_pose_question"
                }
            }
        )
        self.dialogue.register_dialogue(
            "director_office_intro",
            {
                "start": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "……你就是新來的修復師？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "工友讓你過來的？那看來他至少沒有把你趕走。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "正好，修復室那邊有一幅畫的底色需要重新調整。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "我要你調出正確的顏色，再回來向我報告。",
                    "action": "receive_color_mixing_task"
                }
            }
        )
        self.dialogue.register_dialogue(
            "director_color_done_report",
            {
                "start": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "……你把顏色調出來了？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "嗯，這個色調確實接近原本的樣子。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "接下來你去特展廳。那裡有一組色碼，我把題目寫在這張紙上。",
                    "action": "receive_special_hall_key_and_color_code_note"
                }
            }
        )
        self.dialogue.register_dialogue(
            "director_color_code_report",
            {
                "start": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "你算出特展廳的色碼了？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "那麼，這三組色碼分別接近什麼顏色？",
                    "action": "start_director_color_code_report"
                }
            }
        )
        self.dialogue.register_dialogue(
            "director_reasoning_1_intro",
            {
                "start": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "色碼也解出來了嗎……",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "看來工友沒有看錯人。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "那麼，我再問你一個問題。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "如果一間美術館反覆修改展間動線，卻刻意保留某些被封住的門，這代表什麼？",
                    "action": "start_director_reasoning_1"
                }
            }
        )
        self.dialogue.register_dialogue(
            "director_idle",
            {
                "start": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "如果有要回報的東西，就先從口袋裡拿出來。",
                    "next": None
                }
            }
        )
        self.dialogue.register_dialogue(
            "worker_light_bulb_intro",
            {
                "start": {
                    "speaker": "工友",
                    "speaker_side": "right",
                    "portrait": "worker",
                    "text": "倉庫裡黑得什麼都看不見？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "工友",
                    "speaker_side": "right",
                    "portrait": "worker",
                    "text": "我就知道那盞燈早晚會壞。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "工友",
                    "speaker_side": "right",
                    "portrait": "worker",
                    "text": "拿去吧。換上之後，應該就能看清楚裡面了。",
                    "action": "receive_light_bulb"
                }
            }
        )
        self.dialogue.register_dialogue(
            "girl_special_hall_intro",
            {
                "start": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "你找到這裡了。",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "那你可以幫我找一幅畫嗎？",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "它叫《太陽之女》。我以前把它看得很久很久。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "不過，在那之前，你還要先回答我第三個問題。",
                    "action": "start_girl_riddle_3"
                }
            }
        )
        self.dialogue.register_dialogue(
            "girl_receive_fake_sunflower",
            {
                "start": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "你找到了？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "……不對。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "這不是它。你根本沒有看清楚。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "如果你真的想找，就照著這個去看。",
                    "action": "girl_gives_diary"
                }
            }
        )
        self.dialogue.register_dialogue(
            "girl_receive_high_quality_sunflower",
            {
                "start": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "你又找到了一幅？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "這一次……真的很像。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "可是它還是不對。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "如果你真的看懂了，就回答我最後一個問題。",
                    "action": "start_girl_riddle_4"
                }
            }
        )
        self.dialogue.register_dialogue(
            "girl_boys_room_truth_hint",
            {
                "start": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "你知道了吧？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "被掛出來的不是它，被收起來的也不是它。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "真正的那幅畫，被蓋在別的顏色下面。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "如果你是修復師，就去修復室看看。",
                    "action": "girl_truth_hint_finished"
                }
            }
        )
        self.dialogue.register_dialogue(
            "girl_receive_true_sunflower",
            {
                "start": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "……",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "是它。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "原來它一直都還在。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "小女孩",
                    "speaker_side": "right",
                    "portrait": "girl",
                    "text": "謝謝你。現在，你也該去找真正把這一切藏起來的人了。",
                    "action": "finish_girl_route"
                }
            }
        )
        self.dialogue.register_dialogue(
            "director_final_truth",
            {
                "start": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "你把照片拼起來了？",
                    "next": "line_2"
                },
                "line_2": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "那孩子……原本不該留在這裡。",
                    "next": "line_3"
                },
                "line_3": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "火災後，我們修復了展間，換掉了動線，也換掉了該被看見的東西。",
                    "next": "line_4"
                },
                "line_4": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "我以為只要把畫藏起來，把記錄改掉，這座美術館就能繼續存在。",
                    "next": "line_5"
                },
                "line_5": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "但被留下來的，不只是畫。",
                    "next": "line_6"
                },
                "line_6": {
                    "speaker": "館長",
                    "speaker_side": "right",
                    "portrait": "director",
                    "text": "拿著這個吧。出口一直都在，只是你看不見。",
                    "action": "receive_color_filter"
                }
            }
        )
    # =========================================================
    # 謎題資料註冊
    # =========================================================
    def register_puzzles(self):
        """
        註冊遊戲中所有謎題資料。
        """

        self.puzzle.register_puzzle(
            "girl_riddle_1",
            {
                "title": "謎語 1",
                "question": "我沒有腳，卻能走遍整間屋子；我沒有嘴，卻會在夜裡說話。你越害怕我，我就越靠近你。我是什麼？",
                "choices": [
                    {
                        "text": "門鎖",
                        "correct": False
                    },
                    {
                        "text": "影子",
                        "correct": True
                    },
                    {
                        "text": "鏡子",
                        "correct": False
                    },
                    {
                        "text": "水聲",
                        "correct": False
                    }
                ],
                "wrong_message": "不對。牆上的水聲變得更近了。",
                "clear_message": "扭曲的空間開始恢復原狀。",
                "clear_action": "clear_girl_riddle_1"
            }
        )

        self.puzzle.register_puzzle(
            "girl_riddle_2",
            {
                "title": "謎語 2",
                "question": "我記得所有人的名字，卻沒有人記得我；我寫下過去，卻不能改變任何事。我是什麼？",
                "choices": [
                    {
                        "text": "鏡子",
                        "correct": False
                    },
                    {
                        "text": "門牌",
                        "correct": False
                    },
                    {
                        "text": "館史",
                        "correct": True
                    },
                    {
                        "text": "火災",
                        "correct": False
                    }
                ],
                "wrong_message": "不對。紙頁上的字跡變得更加模糊。",
                "clear_message": "館史室的文字逐漸恢復原狀。",
                "clear_action": "clear_girl_riddle_2"
            }
        )
        self.puzzle.register_puzzle(
            "worker_pose_question",
            {
                "title": "工友的提問",
                "question": "工友指著一尊微微前傾的雕像問你：「如果一個人物的重心落在前腳，肩線卻往後收，這個姿勢最可能表現的是什麼？」",
                "choices": [
                    {"text": "完全放鬆地站著", "correct": False},
                    {"text": "已經倒下", "correct": False},
                    {"text": "正準備往前移動", "correct": True},
                    {"text": "正在睡覺", "correct": False}
                ],
                "wrong_message": "工友皺了皺眉。看來你沒看懂雕像的動勢。",
                "clear_message": "工友沒有立刻說話。",
                "clear_action": "clear_worker_pose_question"
            }
        )
        self.puzzle.register_puzzle(
            "fix_room_color_mixing_1",
            {
                "title": "調色任務 1",
                "question": "色票第一格呈現暗金棕色。若要調出舊油畫底層常見的暗金棕，最合理的組合是哪一個？",
                "choices": [
                    {"text": "純白、亮藍、大量紅色", "correct": False},
                    {"text": "赭石、少量黑、些微黃色", "correct": True},
                    {"text": "螢光綠、紫色、銀色", "correct": False},
                    {"text": "大量黑色，不加入其他顏色", "correct": False}
                ],
                "wrong_message": "顏色不對。畫布上的陰影像是又往外擴散了一點。",
                "clear_message": "第一格顏色完成。",
                "clear_action": "clear_fix_room_color_mixing_1"
            }
        )

        self.puzzle.register_puzzle(
            "fix_room_color_mixing_2",
            {
                "title": "調色任務 2",
                "question": "第二格顏色偏灰綠，像是長年受潮後的銅綠陰影。哪一組調法最接近？",
                "choices": [
                    {"text": "亮紅、大量白色、黃色", "correct": False},
                    {"text": "純黑、純白各半", "correct": False},
                    {"text": "深綠、少量灰、些微藍色", "correct": True},
                    {"text": "粉紅、金色、橘色", "correct": False}
                ],
                "wrong_message": "不對。顏料變得混濁，空氣裡的霉味更重了。",
                "clear_message": "第二格顏色完成。",
                "clear_action": "clear_fix_room_color_mixing_2"
            }
        )

        self.puzzle.register_puzzle(
            "fix_room_color_mixing_3",
            {
                "title": "調色任務 3",
                "question": "最後一格顏色接近泛黃的舊紙色。要讓白色變得像老紙一樣溫濁，最適合加入什麼？",
                "choices": [
                    {"text": "大量螢光藍", "correct": False},
                    {"text": "純紫色與銀色", "correct": False},
                    {"text": "少量赭石與淡黃", "correct": True},
                    {"text": "鮮紅色與亮綠色", "correct": False}
                ],
                "wrong_message": "不對。色票上的顏色像是被水漬吞掉了一角。",
                "clear_message": "三格顏色都完成了。",
                "clear_action": "clear_fix_room_color_mixing_3"
            }
        )

        self.puzzle.register_puzzle(
            "special_hall_color_code_1",
            {
                "title": "色碼運算 1",
                "question": "第一題：RGB(10, 20, 90) + RGB(5, 10, 60) = ?",
                "choices": [
                    {"text": "RGB(20, 30, 140)", "correct": False},
                    {"text": "RGB(15, 20, 160)", "correct": False},
                    {"text": "RGB(15, 30, 150)", "correct": True},
                    {"text": "RGB(30, 15, 150)", "correct": False}
                ],
                "wrong_message": "不對。牆上的第一組色塊重新閃爍起來。",
                "clear_message": "第一組色碼完成。",
                "clear_action": "clear_special_hall_color_code_1"
            }
        )

        self.puzzle.register_puzzle(
            "special_hall_color_code_2",
            {
                "title": "色碼運算 2",
                "question": "第二題：#201000 + #40220E = ?",
                "choices": [
                    {"text": "#60220E", "correct": False},
                    {"text": "#40320E", "correct": False},
                    {"text": "#623010", "correct": False},
                    {"text": "#60320E", "correct": True}
                ],
                "wrong_message": "不對。第二組色塊像是被覆上一層暗影。",
                "clear_message": "第二組色碼完成。",
                "clear_action": "clear_special_hall_color_code_2"
            }
        )

        self.puzzle.register_puzzle(
            "special_hall_color_code_3",
            {
                "title": "色碼運算 3",
                "question": "第三題：#102010 + #203020 + #304030 = ?",
                "choices": [
                    {"text": "#609060", "correct": False},
                    {"text": "#60A060", "correct": True},
                    {"text": "#50A060", "correct": False},
                    {"text": "#60A050", "correct": False}
                ],
                "wrong_message": "不對。第三組色塊變得更加混濁。",
                "clear_message": "三組色碼都算出來了。",
                "clear_action": "clear_special_hall_color_code_3"
            }
        )
        self.puzzle.register_puzzle(
            "director_color_code_report",
            {
                "title": "色碼判讀",
                "question": "館長問你：這三組色碼分別接近什麼顏色？",
                "choices": [
                    {"text": "暗紅、亮黃、淺紫", "correct": False},
                    {"text": "深藍、深咖啡、淺墨綠", "correct": True},
                    {"text": "純黑、純白、亮藍", "correct": False},
                    {"text": "灰綠、粉紅、橘黃", "correct": False}
                ],
                "wrong_message": "館長皺起眉頭。這不是他要的答案。",
                "clear_message": "館長點了點頭。",
                "clear_action": "clear_director_color_code_report"
            }
        )
        self.puzzle.register_puzzle(
            "director_reasoning_1",
            {
                "title": "館長推理 1",
                "question": "如果一間美術館反覆修改展間動線，卻刻意保留某些被封住的門，最合理的推論是什麼？",
                "choices": [
                    {
                        "text": "只是為了讓參觀路線更美觀",
                        "correct": False
                    },
                    {
                        "text": "那些門後可能藏著改建前留下的空間或秘密",
                        "correct": True
                    },
                    {
                        "text": "館長單純不喜歡直線動線",
                        "correct": False
                    },
                    {
                        "text": "美術館想讓遊客多走一點路",
                        "correct": False
                    }
                ],
                "wrong_message": "館長沒有說話，只是靜靜看著你。",
                "clear_message": "館長似乎接受了你的推論。",
                "clear_action": "clear_director_reasoning_1"
            }
        )


        self.puzzle.register_puzzle(
            "girl_riddle_3",
            {
                "title": "謎語 3",
                "question": "我被掛在牆上，卻不是為了被看見；我有名字，卻常被換成別人的臉。我越像真的，就越不像我自己。我是什麼？",
                "choices": [
                    {"text": "窗戶", "correct": False},
                    {"text": "贗品", "correct": True},
                    {"text": "門鎖", "correct": False},
                    {"text": "影子", "correct": False}
                ],
                "wrong_message": "不對。牆上的畫框微微傾斜了一下。",
                "clear_message": "特展廳的空氣逐漸恢復平靜。",
                "clear_action": "clear_girl_riddle_3"
            }
        )
        self.puzzle.register_puzzle(
            "girl_riddle_4",
            {
                "title": "謎語 4",
                "question": "我比第一個更像，卻仍然不是我；我靠近真相，卻沒有真正的心。越是完整，越證明我只是複製。這代表什麼？",
                "choices": [
                    {"text": "這幅畫是真跡", "correct": False},
                    {"text": "這幅畫也是假的", "correct": True},
                    {"text": "畫框才是真正的線索", "correct": False},
                    {"text": "日記記錯了內容", "correct": False}
                ],
                "wrong_message": "不對。小女孩沉默地盯著你手中的畫。",
                "clear_message": "小女孩慢慢低下頭。",
                "clear_action": "clear_girl_riddle_4"
            }
        )
    # =========================================================
    # NPC 對話控制
    # =========================================================
    def start_dialogue(self, dialogue_id):
        started = self.dialogue.start(dialogue_id)

        if not started:
            return

        self.dialogue_return_mode = self.mode
        self.mode = "dialogue"

        self.pocket_open = False
        self.stop_walk_sound()
        self.pause_game_time()

    def advance_dialogue(self):
        result = self.dialogue.advance()

        if result == "ended":
            self.finish_dialogue()

    def choose_dialogue_option(self, choice_index):
        result = self.dialogue.choose(choice_index)

        if result == "ended":
            self.finish_dialogue()

    def finish_dialogue(self):
        action = self.dialogue.consume_pending_end_action()

        self.mode = self.dialogue_return_mode
        self.dialogue_return_mode = "observation"

        self.resume_game_time()

        if action:
            self.handle_dialogue_action(action)
    def clear_fix_room_color_mixing_1_event(self):
        self.story.set_director_flag("color_mixing_question_1_cleared")
        self.set_system_message("第一格顏色完成。")
        self.puzzle.start_puzzle("fix_room_color_mixing_2")


    def clear_fix_room_color_mixing_2_event(self):
        self.story.set_director_flag("color_mixing_question_2_cleared")
        self.set_system_message("第二格顏色完成。")
        self.puzzle.start_puzzle("fix_room_color_mixing_3")

    def clear_fix_room_color_mixing_3_event(self):
        self.story.set_director_flag("color_mixing_question_3_cleared")
        self.story.set_director_flag("color_mixing_task_cleared")
        self.story.set_director_flag("color_done_obtained")

        self.clear_mutated_room("fix_room")

        item = self.get_collectible_item("color_done")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "最後一格顏色也完成了。",
            "三種顏色在調色盤上安靜地沉澱下來。",
            "你獲得了【調色盤】。",
            "也許該回館長室向館長報告。"
        ])
    def receive_special_hall_key_and_color_code_note_event(self):
        self.active_item_id = None
        self.remove_item_from_inventory("color_done")
        """
        館長確認調色盤後：
        - 給玩家特展廳鑰匙
        - 給玩家色碼題紙
        - 開啟特展廳色碼任務
        """
        self.story.set_director_flag("special_key_obtained")
        self.story.set_director_flag("color_code_note_obtained")
        self.story.set_director_flag("special_hall_task_received")

        for item_id in ["special_key", "color_code_note"]:
            item = self.get_collectible_item(item_id)

            if item:
                item["collected"] = True

                if item["name"] not in self.inventory.items:
                    self.inventory.items.append(item["name"])

        self.start_message_reading([
            "館長收下了你完成的調色盤。",
            "他從抽屜裡取出一把鑰匙，以及一張寫滿色碼的紙。",
            "你獲得了【特展廳鑰匙】。",
            "你獲得了【色碼題紙】。",
            "館長要你前往特展廳，解出那裡留下的色碼。"
        ])
    def start_director_color_code_report_event(self):
        self.active_item_id = None
        self.remove_item_from_inventory("calculated_color_codes")
        """
        回館長室交出算出的色碼後，進入顏色名稱判斷題。
        """
        self.story.set_director_flag("director_color_code_report_started")
        self.puzzle.start_puzzle("director_color_code_report")
    def start_director_reasoning_1_event(self):
        self.active_item_id = None
        """
        館長推理 1：
        - 館長室變異
        - 啟動推理 1
        """
        self.story.set_director_flag("director_reasoning_1_started")

        self.set_system_message(
            "館長室的燈光暗了下來，牆上的畫框像是微微偏移。"
        )

        self.start_mutated_room(
            "office",
            sanity_decay_per_second=1.2
        )

        self.puzzle.start_puzzle("director_reasoning_1")
    
    
    def start_girl_riddle_3_event(self):
        """
        特展廳小女孩對話結束後：
        - 紀錄謎語 3 已開始
        - 特展廳進入變異狀態
        - 啟動謎題 3
        """
        self.story.set_girl_flag("sunflower_girl_request_received")
        self.story.set_girl_flag("girl_riddle_3_started")

        self.set_system_message(
            "特展廳的燈光開始閃爍，畫框裡的臉像是慢慢被誰擦掉。"
        )

        self.start_mutated_room(
            "special_hall",
            sanity_decay_per_second=1.2
        )

        self.puzzle.start_puzzle("girl_riddle_3")

    def should_show_girls_room_girl_after_true_painting(self):
        """
        玩家取得真正的《太陽之女》後，
        小女孩會在女廁等待玩家交出真跡。
        這裡同時檢查劇情旗標與道具持有狀態，避免其中一邊漏設導致小女孩不出現。
        """
        true_painting_item = self.get_collectible_item("true_sunflower_painting")

        has_true_painting_item = (
            true_painting_item is not None
            and true_painting_item.get("collected", False)
        )

        return (
            self.observation_scene_id == "girls_room"
            and (
                self.story.has_girl_flag("true_sunflower_obtained")
                or has_true_painting_item
            )
            and not self.story.has_girl_flag("true_sunflower_given_to_girl")
            and not self.story.has_girl_flag("girl_route_finished")
        )
    def should_show_girls_room_girl_after_high_quality_painting(self):
        """
        玩家取得第二幅《太陽之女》後，
        小女孩會在女廁等待玩家交畫並觸發謎語 4。
        謎語 4 通關後，小女孩不應該再停留在女廁。
        """
        return (
            self.observation_scene_id == "girls_room"
            and self.story.has_girl_flag("high_quality_fake_sunflower_obtained")
            and not self.story.has_girl_flag("high_quality_sunflower_given_to_girl")
            and not self.story.has_girl_flag("girl_riddle_4_cleared")
            and not self.story.has_girl_flag("true_sunflower_obtained")
        )


    def should_show_boys_room_girl_after_riddle_4(self):
        """
        謎語 4 完成後，小女孩移動到男廁。
        """
        return (
            self.observation_scene_id == "boys_room"
            and self.story.has_girl_flag("girl_moved_to_boys_room")
            and not self.story.has_girl_flag("boys_room_truth_hint_finished")
        )


    def get_boys_room_girl_rect(self):
        """
        小女孩在男廁中的顯示與點擊區。
        """
        return pygame.Rect(
            760,
            185,
            180,
            330
        )


    def start_girl_riddle_4_event(self):
        """
        交第二幅《太陽之女》後，啟動謎語 4。
        """
        self.active_item_id = None

        self.story.set_girl_flag("high_quality_sunflower_given_to_girl")
        self.story.set_girl_flag("girl_riddle_4_started")

        self.set_system_message("女廁的鏡面開始泛起細小的裂紋。")

        self.start_mutated_room(
            "girls_room",
            sanity_decay_per_second=1.2
        )

        self.puzzle.start_puzzle("girl_riddle_4")


    def clear_girl_riddle_4_event(self):
        """
        謎語 4 完成後：
        - 解除女廁變異
        - 小女孩移動到男廁
        - 同時開啟修復室真跡線索，避免玩家卡住
        """
        self.story.set_girl_flag("girl_riddle_4_cleared")
        self.story.set_girl_flag("girl_moved_to_boys_room")
        self.story.set_girl_flag("true_sunflower_hint_received")

        self.clear_mutated_room("girls_room")

        self.start_message_reading([
            "小女孩沒有再看那幅畫。",
            "她只是低聲說：",
            "「它太像了，所以才不是它。」",
            "「真正的那幅畫，被蓋在別的顏色下面。」",
            "「去修復室看看。桌上的舊畫，也許不是表面看起來的樣子。」"
        ])


    def girl_truth_hint_finished_event(self):
        """
        男廁小女孩提示完成後，引導玩家去修復室尋找真跡。
        """
        self.story.set_girl_flag("boys_room_truth_hint_finished")
        self.story.set_girl_flag("true_sunflower_hint_received")

        self.start_message_reading([
            "小女孩的身影在男廁的水氣中變得模糊。",
            "你想起館長一開始交給你的修復任務。",
            "如果真正的《太陽之女》被蓋在別的顏色下面，",
            "那麼修復室也許就是最後的線索。"
        ])


    def get_fix_room_true_painting_rect(self):
        """
        修復室真跡互動區。
        """
        return pygame.Rect(
            500,
            275,
            280,
            150
        )


    def inspect_fix_room_true_painting(self):
        """
        在修復室刮除表層，取得真正的《太陽之女》。
        """
        if (
            not self.story.has_girl_flag("true_sunflower_hint_received")
            and not self.story.has_girl_flag("girl_riddle_4_cleared")
        ):
            self.set_system_message("修復桌上擺著工具，但你還不知道該修復什麼。")
            return
        if self.story.has_girl_flag("true_sunflower_obtained"):
            self.set_system_message("你已經取回真正的《太陽之女》了。")
            return

        self.story.set_girl_flag("true_sunflower_obtained")
        self.story.set_girl_flag("true_sunflower_ready_to_return")
        self.replace_sunflower_painting_item("true_sunflower_painting")
        
        self.start_message_reading([
            "表層的顏料和底層並不相連，像是後來才被刻意覆蓋上去。",
            "你小心刮除表層，底下逐漸露出一名全身泛著柔光的女孩。",
            "那幅畫一直被藏在另一幅畫的下面。",
            "你獲得了【太陽之女】。"
        ])


    def finish_girl_route_event(self):
        """
        小女孩線結束。
        """
        self.active_item_id = None
        self.remove_item_from_inventory("true_sunflower_painting")

        self.story.set_girl_flag("true_sunflower_given_to_girl")
        self.story.set_girl_flag("girl_route_finished")

        self.start_message_reading([
            "小女孩抱著那幅畫，身影逐漸變得透明。",
            "她回頭看了你一眼。",
            "「照片……也該完整了。」",
            "她消失後，五片照片一角開始微微發熱。",
            "你將它們拼在一起。",
            "照片上，是館長與小女孩站在《太陽之女》前的合照。",
            "你獲得了【拼好的照片】。",
            "也許現在該拿著這張照片，去找館長問清楚一切。"
        ])
        self.story.set_main_flag("photo_completed")

        photo_item = self.get_collectible_item("photo_complete")

        if photo_item:
            photo_item["collected"] = True

            if photo_item["name"] not in self.inventory.items:
                self.inventory.items.append(photo_item["name"])

    def should_trigger_director_final_truth(self):
        """
        玩家必須使用【拼好的照片】點擊館長，才會觸發最終真相。
        為了避免 photo_completed 旗標漏設，這裡直接以 active_item_id 為主。
        """
        return (
            self.observation_scene_id == "office"
            and self.active_item_id == "photo_complete"
            and not self.story.has_director_flag("director_final_truth_started")
        )


    def receive_color_filter_event(self):
        """
        館長最終真相後取得遮色片。
        """
        self.story.set_director_flag("director_final_truth_started")
        self.story.set_director_flag("director_final_truth_cleared")
        self.story.set_director_flag("color_filter_obtained")

        item = self.get_collectible_item("color_filter")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "館長將一片透明的遮色片放到你手中。",
            "你獲得了【遮色片】。",
            "他低聲說：",
            "「去男廁看看吧。」",
            "「那裡的窗戶，從來不是窗戶。」"
        ])


    def get_boys_room_exit_rect(self):
        """
        男廁出口互動區。
        使用遮色片後，可發現真正出口。
        """
        return pygame.Rect(
            875,
            160,
            220,
            260
        )


    def inspect_boys_room_exit_with_filter(self):
        """
        使用遮色片查看男廁窗戶，發現出口。
        """
        if self.active_item_id != "color_filter":
            self.set_system_message("也許可以用館長留下的遮色片看看。")
            return

        self.active_item_id = None
        self.true_exit_found = True

        self.start_message_reading([
            "你將遮色片舉到眼前。",
            "男廁窗戶上的污漬慢慢排列成一道清晰的輪廓。",
            "那不是窗戶。",
            "那是一扇被偽裝起來的出口。",
            "出口出現了。"
        ])

    def handle_dialogue_action(self, action):
        """
        對話結束後觸發後續劇情。
        """

        if action == "start_girl_riddle_1":
            self.start_girl_riddle_1_event()
            
        elif action == "start_girl_riddle_2":
            self.start_girl_riddle_2_event()

        elif action == "start_worker_pose_question":
            self.start_worker_pose_question_event()

        elif action == "receive_color_mixing_task":
            self.receive_color_mixing_task_event()
        elif action == "clear_fix_room_color_mixing_1":
            self.clear_fix_room_color_mixing_1_event()

        elif action == "clear_fix_room_color_mixing_2":
            self.clear_fix_room_color_mixing_2_event()

        elif action == "clear_fix_room_color_mixing_3":
            self.clear_fix_room_color_mixing_3_event()

        elif action == "receive_special_hall_key_and_color_code_note":
            self.receive_special_hall_key_and_color_code_note_event()

        elif action == "start_director_color_code_report":
            self.start_director_color_code_report_event()

        elif action == "start_director_reasoning_1":
            self.start_director_reasoning_1_event()
        
        elif action == "receive_light_bulb":
            self.receive_light_bulb_event()   
        
        elif action == "start_girl_riddle_3":
            self.start_girl_riddle_3_event() 

        elif action == "girl_gives_diary":
            self.girl_gives_diary_event()

        elif action == "start_girl_riddle_4":
            self.start_girl_riddle_4_event()

        elif action == "girl_truth_hint_finished":
            self.girl_truth_hint_finished_event()

        elif action == "finish_girl_route":
            self.finish_girl_route_event()

        elif action == "receive_color_filter":
            self.receive_color_filter_event()
    # =========================================================
    # 遊戲時間
    # =========================================================
    def pause_game_time(self):
        if not self.time_paused:
            self.time_paused = True
            self.pause_started_at = time.time()

    def resume_game_time(self):
        if self.time_paused:
            pause_duration = time.time() - self.pause_started_at
            self.total_paused_duration += pause_duration

            self.time_paused = False
            self.pause_started_at = None

    def update_game_time(self):
        now = time.time()

        if self.time_paused:
            effective_elapsed = (
                self.pause_started_at
                - self.real_start_time
                - self.total_paused_duration
            )
        else:
            effective_elapsed = (
                now
                - self.real_start_time
                - self.total_paused_duration
            )

        # 遊戲內時間流速：現實 15 秒 = 遊戲 1 分鐘
        self.game_minutes = 23 * 60 + 47 + int(effective_elapsed / 15)

        if self.game_minutes >= 24 * 60:
            display_minutes = self.game_minutes - 24 * 60
        else:
            display_minutes = self.game_minutes

        hour = display_minutes // 60
        minute = display_minutes % 60

        return f"{hour:02d}:{minute:02d}"

    # =========================================================
    # 訊息讀取狀態
    # =========================================================
    def start_message_reading(self, messages):
        if not messages:
            return

        self.pocket_open = False
        self.stop_walk_sound()

        self.message_reading = True
        self.story_messages = messages
        self.story_message_index = 0
        self.current_story_message = self.story_messages[0]

        self.reset_typewriter_slot("bottom_main")
        self.reset_typewriter_slot("bottom_sub")

        self.pause_game_time()

    def advance_message_reading(self):
        if not self.message_reading:
            return

        if not self.is_typewriter_complete("bottom_main", self.current_story_message):
            self.complete_typewriter("bottom_main", self.current_story_message)
            return

        self.story_message_index += 1
        if self.story_message_index < len(self.story_messages):
            self.current_story_message = self.story_messages[self.story_message_index]

            self.reset_typewriter_slot("bottom_main")
            self.reset_typewriter_slot("bottom_sub")

            # 開場大門上鎖演出
            if self.current_story_message == "「喀嚓。」":
                self.play_lock_sound()
                self.start_screen_shake()
        else:
            self.end_message_reading()

    def end_message_reading(self):
        self.message_reading = False
        self.story_messages = []
        self.story_message_index = 0
        self.current_story_message = ""

        self.reset_typewriter_slot("bottom_main")
        self.reset_typewriter_slot("bottom_sub")

        self.resume_game_time()

        if self.control_hint_pending:
            self.control_hint_expire_time = time.time() + 5
            self.control_hint_pending = False
        if self.pending_return_to_menu_after_messages:
            self.pending_return_to_menu_after_messages = False
            self.return_to_main_menu()

    # =========================================================
    # 系統訊息
    # =========================================================
    def set_system_message(self, text):
        self.system_message = text
        self.system_message_start_time = time.time()

        self.reset_typewriter_slot("bottom_main")

    def get_system_message(self):
        if not self.system_message:
            return ""

        elapsed = time.time() - self.system_message_start_time

        if elapsed <= self.system_message_duration:
            return self.system_message

        self.system_message = ""
        self.system_message_start_time = 0
        self.reset_typewriter_slot("bottom_main")
        return ""

    def should_show_control_hint(self):
        return time.time() <= self.control_hint_expire_time


    def get_sfx_slider_rect(self):
        panel = self.get_pause_panel_rect()

        return pygame.Rect(
            panel.x + 230,
            panel.y + 325,
            330,
            12
        )
    
    def update_sfx_volume_from_mouse(self, mouse_x):
        slider = self.get_sfx_slider_rect()

        ratio = (mouse_x - slider.x) / slider.width
        ratio = max(0.0, min(1.0, ratio))

        self.sfx_volume_ratio = ratio

        if self.open_door_sound:
            self.open_door_sound.set_volume(0.35 * self.sfx_volume_ratio)

        if self.walk_sound:
            self.walk_sound.set_volume(1.0 * self.sfx_volume_ratio)

        if self.lock_sound:
            self.lock_sound.set_volume(0.28 * self.sfx_volume_ratio)
    # =========================================================
    # 打字機效果
    # =========================================================
    def create_empty_typewriter_slot(self):
        return {
            "full_text": "",
            "visible_count": 0,
            "last_update_time": time.time()
        }

    def reset_typewriter_slot(self, slot_name):
        self.typewriter_slots[slot_name] = self.create_empty_typewriter_slot()

    def reset_all_typewriters(self):
        for slot_name in self.typewriter_slots:
            self.reset_typewriter_slot(slot_name)

    def get_typewriter_text(self, slot_name, full_text):
        slot = self.typewriter_slots[slot_name]

        if not full_text:
            if slot["full_text"]:
                self.reset_typewriter_slot(slot_name)
            return ""

        if slot["full_text"] != full_text:
            slot["full_text"] = full_text
            slot["visible_count"] = 0
            slot["last_update_time"] = time.time()

        now = time.time()
        elapsed = now - slot["last_update_time"]

        if elapsed >= self.typewriter_speed:
            letters_to_add = int(elapsed / self.typewriter_speed)

            slot["visible_count"] = min(
                len(slot["full_text"]),
                slot["visible_count"] + letters_to_add
            )

            slot["last_update_time"] = now

        return slot["full_text"][:slot["visible_count"]]

    def is_typewriter_complete(self, slot_name, full_text):
        slot = self.typewriter_slots[slot_name]

        return (
            slot["full_text"] == full_text
            and slot["visible_count"] >= len(full_text)
        )

    def complete_typewriter(self, slot_name, full_text):
        slot = self.typewriter_slots[slot_name]

        slot["full_text"] = full_text
        slot["visible_count"] = len(full_text)
        slot["last_update_time"] = time.time()

    # =========================================================
    # 音效系統
    # =========================================================
    def switch_to_mutation_bgm(self):
        """
        進入變異空間時切換 BGM。
        目前 mutation_bgm_path 為空，所以先靜音。
        之後有變異音樂時，只要設定 mutation_bgm_path 即可。
        """
        if self.using_mutation_bgm:
            return

        self.using_mutation_bgm = True

        # 目前沒有準備變異 BGM，所以先停止音樂
        if not self.mutation_bgm_path:
            pygame.mixer.music.stop()
            return

        try:
            pygame.mixer.music.load(self.mutation_bgm_path)
            pygame.mixer.music.set_volume(
                self.bgm_max_volume * self.bgm_volume_ratio
            )
            pygame.mixer.music.play(-1)
        except pygame.error:
            print("[警告] 無法載入變異 BGM：", self.mutation_bgm_path)


    def switch_to_normal_bgm(self):
        """
        解除變異空間後恢復普通 BGM。
        """
        if not self.using_mutation_bgm:
            return

        self.using_mutation_bgm = False

        if not self.bgm_loaded:
            return

        try:
            pygame.mixer.music.load(self.bgm_path)
            pygame.mixer.music.set_volume(
                self.bgm_max_volume * self.bgm_volume_ratio
            )
            pygame.mixer.music.play(-1)
        except pygame.error:
            print("[警告] 無法恢復 BGM.mp3")

    def play_open_door_sound(self):
        if self.open_door_sound:
            self.open_door_sound.play()

    def play_lock_sound(self):
        if self.lock_sound:
            self.lock_sound.play()

    def update_walk_sound(self):
        should_play = (
            self.mode == "hallway"
            and self.hallway.player_is_moving
            and not self.pocket_open
            and not self.message_reading
        )

        if should_play:
            if self.walk_sound and self.walk_sound_channel is None:
                self.walk_sound_channel = self.walk_sound.play(loops=-1)

            elif (
                self.walk_sound
                and self.walk_sound_channel is not None
                and not self.walk_sound_channel.get_busy()
            ):
                self.walk_sound_channel = self.walk_sound.play(loops=-1)

        else:
            self.stop_walk_sound()

    def stop_walk_sound(self):
        if self.walk_sound_channel is not None:
            self.walk_sound_channel.stop()
            self.walk_sound_channel = None

    # =========================================================
    # 畫面震動系統
    # =========================================================
    def start_screen_shake(self):
        self.screen_shake_active = True
        self.screen_shake_start_time = time.time()

    def get_screen_shake_offset(self):
        if not self.screen_shake_active:
            return (0, 0)

        elapsed = time.time() - self.screen_shake_start_time
        step_index = int(elapsed / self.screen_shake_step_duration)

        if step_index >= len(self.screen_shake_offsets):
            self.screen_shake_active = False
            return (0, 0)

        return self.screen_shake_offsets[step_index]

    def apply_screen_shake(self):
        offset_x, offset_y = self.get_screen_shake_offset()

        if offset_x == 0 and offset_y == 0:
            return

        current_frame = self.screen.copy()

        self.screen.fill((10, 9, 10))
        self.screen.blit(current_frame, (offset_x, offset_y))

    # =========================================================
    # 互動區：修復室 → 倉庫
    # =========================================================
    def get_fix_room_storage_hotspot_rect(self):
        hotspot_size = 190
        view_y = 80
        view_height = 500

        center_x = WIDTH // 2 - 10
        center_y = view_y + view_height // 2 - 50

        return pygame.Rect(
            center_x - hotspot_size // 2,
            center_y - hotspot_size // 2,
            hotspot_size,
            hotspot_size
        )

    # =========================================================
    # 可拾取互動道具系統
    # =========================================================
    def reset_collectible_items(self):
        self.collectible_items = {
            "toilet_key": {
                "id": "toilet_key",
                "name": "廁所鑰匙",
                "scene_id": "boys_room",
                "image_filename": "toilet_key.png",
                "description": "兩把串在一起的老舊鑰匙。看起來似乎分別能打開男廁與女廁的門。",
                # 原本 120 × 90，現在縮小一半為 60 × 45
                "scene_rect": pygame.Rect(420, 250, 60, 45),
                "collected": False
            },
            "office_key": {
                "id": "office_key",
                "name": "館長室鑰匙",
                "scene_id": None,
                "image_filename": "office_key.png",
                "description": "工友交給你的鑰匙。看起來可以打開館長室。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },
            "correct_color": {
                "id": "correct_color",
                "name": "正確的顏色",
                "scene_id": None,
                "image_filename": "correct_color.png",
                "description": "你在修復室調出的顏色。色澤與館長給你的色票幾乎一致。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },
            "color_ticket": {
                "id": "color_ticket",
                "name": "色票",
                "scene_id": None,
                "image_filename": "color_ticket.png",
                "description": "館長交給你的舊色票。上面留下幾格褪色的顏色樣本，似乎是修復用的參考。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },
            "color_done": {
                "id": "color_done",
                "name": "調色盤",
                "scene_id": None,
                "image_filename": "color_done.png",
                "description": "你在修復室完成的調色盤。顏色與館長交給你的色票十分接近。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },
            "special_key": {
                "id": "special_key",
                "name": "特展廳鑰匙",
                "scene_id": None,
                "image_filename": "special_key.png",
                "description": "館長交給你的鑰匙。看起來可以打開特展廳。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },

            "portrait_key": {
                "id": "portrait_key",
                "name": "肖像館鑰匙",
                "scene_id": None,
                "image_filename": "portrait_key.png",
                "description": "小女孩交給你的鑰匙。看起來可以打開肖像展廳。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },

            "color_code_note": {
                "id": "color_code_note",
                "name": "色碼題紙",
                "scene_id": None,
                "image_filename": "color_code_note.png",
                "description": "館長寫下的色碼題紙，上面有三道顏色運算題。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },

            "calculated_color_codes": {
                "id": "calculated_color_codes",
                "name": "算出的色碼",
                "scene_id": None,
                "image_filename": "calculated_color_codes.png",
                "description": "你在特展廳完成三道色碼運算後得到的結果。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },

            "unknown_key": {
                "id": "unknown_key",
                "name": "未知的鑰匙",
                "scene_id": None,
                "image_filename": "unknown_key.png",
                "description": "館長交給你的鑰匙。他說，這種重要的東西，還是由你保管比較好。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },
            "storage_key": {
                "id": "storage_key",
                "name": "倉庫鑰匙",
                "scene_id": None,
                "image_filename": "storage_key.png",
                "description": "從館長室保險箱中取得的鑰匙。看起來可以打開倉庫。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },
            "light_bulb": {
                "id": "light_bulb",
                "name": "新燈泡",
                "scene_id": None,
                "image_filename": "light_bulb.png",
                "description": "工友交給你的新燈泡。也許可以讓漆黑的倉庫重新亮起來。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },

            "newspaper_clipping": {
                "id": "newspaper_clipping",
                "name": "舊報紙",
                "scene_id": None,
                "image_filename": "newspaper_clipping.png",
                "description": "一份泛黃的舊報紙。邊緣有燒焦的痕跡，似乎記錄了多年前美術館火災與改建的消息。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },

            "high_quality_fake_sunflower": {
                "id": "high_quality_fake_sunflower",
                "name": "太陽之女",
                "scene_id": None,
                "image_filename": "high_quality_fake_sunflower.png",
                "description": "一幅幾乎能以假亂真的《太陽之女》。畫面與日記中的描述十分接近。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },

            "fake_sunflower_painting": {
                "id": "fake_sunflower_painting",
                "name": "太陽之女",
                "scene_id": "portraits_hall",
                "image_filename": "fake_sunflower_painting.png",
                "description": "一幅名為《太陽之女》的畫。畫面雖然完整，但筆觸與顏色都有些僵硬。",
                "scene_rect": pygame.Rect(545, 205, 190, 210),
                "collected": False
            },
            "diary": {
                "id": "diary",
                "name": "日記",
                "scene_id": None,
                "image_filename": "diary.png",
                "description": "一本邊角燒焦的舊日記。裡面反覆寫著《太陽之女》的細節。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },
            "true_sunflower_painting": {
                "id": "true_sunflower_painting",
                "name": "太陽之女",
                "scene_id": None,
                "image_filename": "true_sunflower_painting.png",
                "description": "一幅名為《太陽之女》的畫。表層顏料被刮除後，底下露出更柔和、更古老的色彩。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },

            "color_filter": {
                "id": "color_filter",
                "name": "遮色片",
                "scene_id": None,
                "image_filename": "color_filter.png",
                "description": "館長留下的透明遮色片。透過它觀看時，某些被隱藏的痕跡會浮現出來。",
                "scene_rect": pygame.Rect(0, 0, 0, 0),
                "collected": False
            },
            "photo_complete": {
            "id": "photo_complete",
            "name": "拼好的照片",
            "scene_id": None,
            "image_filename": "photo_complete.png",
            "description": "五片照片一角拼合後形成的照片。照片裡，館長與小女孩站在《太陽之女》前。",
            "scene_rect": pygame.Rect(0, 0, 0, 0),
            "collected": False
        },
        }

    def get_collectible_item(self, item_id):
        return self.collectible_items.get(item_id)
    
    def remove_item_from_inventory(self, item_id):
        """
        從口袋移除指定道具。
        道具本身 collected 可保留，避免場景道具重新出現。
        """
        item = self.get_collectible_item(item_id)

        if item is None:
            return

        item_name = item["name"]

        self.inventory.items = [
            name for name in self.inventory.items
            if name != item_name
        ]

        if item_id in [
            "fake_sunflower_painting",
            "high_quality_fake_sunflower",
            "true_sunflower_painting"
        ]:
            item["owned"] = False

    def get_collectible_item_by_name(self, item_name):
        """
        依口袋顯示名稱找道具。
        三幅《太陽之女》同名時，只回傳目前口袋持有中的版本。
        """
        if item_name == "太陽之女":
            sunflower_priority = [
                "true_sunflower_painting",
                "high_quality_fake_sunflower",
                "fake_sunflower_painting"
            ]

            for item_id in sunflower_priority:
                item = self.get_collectible_item(item_id)

                if (
                    item
                    and item["collected"]
                    and item.get("owned", False)
                ):
                    return item

            return None

        for item in self.collectible_items.values():
            if item["name"] == item_name and item["collected"]:
                return item

        return None
    def is_collectible_collected(self, item_id):
        item = self.get_collectible_item(item_id)

        if item is None:
            return False

        return item["collected"]

    def get_visible_collectible_items(self, scene_id):
        visible_items = []

        for item in self.collectible_items.values():
            if item["scene_id"] == scene_id and not item["collected"]:
                visible_items.append(item)

        return visible_items

    def get_collectible_item_at_pos(self, scene_id, mouse_pos):
        for item in self.get_visible_collectible_items(scene_id):
            if item["scene_rect"].collidepoint(mouse_pos):
                return item

        return None

    def start_item_preview(self, item_id):
        item = self.get_collectible_item(item_id)

        if item is None:
            return

        self.stop_walk_sound()
        self.pocket_open = False

        self.preview_item_id = item_id
        self.preview_return_mode = self.mode
        self.preview_return_scene_id = self.observation_scene_id
        self.preview_return_location_name = self.observation_location_name

        self.mode = "item_preview"
        self.pause_game_time()

    def collect_preview_item(self):
        item = self.get_collectible_item(self.preview_item_id)

        if item is not None:
            if item["id"] == "fake_sunflower_painting":
                self.replace_sunflower_painting_item("fake_sunflower_painting")
                self.story.set_girl_flag("fake_sunflower_painting_obtained")

            else:
                item["collected"] = True

                if item["name"] not in self.inventory.items:
                    self.inventory.items.append(item["name"])

            self.set_system_message(f"已將「{item['name']}」收入口袋。")

        self.mode = "observation"
        self.observation_scene_id = self.preview_return_scene_id
        self.observation_location_name = self.preview_return_location_name

        self.preview_item_id = None
        self.preview_return_mode = "observation"
        self.preview_return_scene_id = None
        self.preview_return_location_name = ""

        self.resume_game_time()
    # =========================================================
    # unlock 碎片取得預覽系統
    # =========================================================
    def start_fragment_preview(
        self,
        fragment_id,
        title,
        description
    ):
        """
        顯示 unlock 碎片取得預覽。
        碎片不進入口袋，而是直接記錄在 StoryManager 中。
        """
        self.stop_walk_sound()
        self.pocket_open = False

        self.preview_fragment_id = fragment_id
        self.preview_fragment_title = title
        self.preview_fragment_description = description

        self.fragment_preview_return_mode = self.mode
        self.fragment_preview_return_scene_id = self.observation_scene_id
        self.fragment_preview_return_location_name = self.observation_location_name

        self.mode = "fragment_preview"
        self.pause_game_time()


    def close_fragment_preview(self):
        """
        玩家按 Space 收下碎片後，回到原本狀態。
        """
        return_mode = self.fragment_preview_return_mode

        self.preview_fragment_id = None
        self.preview_fragment_title = ""
        self.preview_fragment_description = ""

        self.fragment_preview_return_mode = "hallway"
        self.fragment_preview_return_scene_id = None
        self.fragment_preview_return_location_name = ""

        self.mode = return_mode
        self.resume_game_time()

        self.set_system_message("你收下了這片照片一角。")
    # =========================================================
    # NPC：女廁小女孩
    # =========================================================
    def should_show_girls_room_girl(self):
        """
        女廁第一次事件：
        - 玩家已經解鎖女廁
        - 已經取得女廁 unlock 碎片
        - 謎語 1 尚未正式開始
        """
        return (
            self.observation_scene_id == "girls_room"
            and self.story.has_main_flag("girls_room_unlocked")
            and self.story.has_main_flag("fragment_from_girls_room_obtained")
            and not self.story.has_main_flag("girl_riddle_1_started")
        )
    def start_girl_riddle_1_event(self):
        """
        小女孩第一次對話結束後：
        - 紀錄謎語 1 已開始
        - 小女孩消失
        - 女廁進入變異狀態
        - 啟動謎題 1
        """

        self.story.set_main_flag("girl_riddle_1_started")

        self.set_system_message(
            "空氣忽然變得濕冷，牆面像是活著一樣緩慢扭曲。"
        )

        self.start_mutated_room(
            "girls_room",
            sanity_decay_per_second=1.2
        )

        self.puzzle.start_puzzle("girl_riddle_1")

    def start_girl_riddle_2_event(self):
        """
        館史室小女孩對話結束後：
        - 紀錄謎語 2 已開始
        - 館史室進入變異狀態
        - 啟動謎題 2
        """

        self.story.set_girl_flag("girl_riddle_2_started")

        self.set_system_message(
            "館史室裡的文字開始滲開，像被水泡爛的墨跡。"
        )

        self.start_mutated_room(
            "history_room",
            sanity_decay_per_second=1.2
        )

        self.puzzle.start_puzzle("girl_riddle_2")

    def get_girls_room_girl_rect(self):
        """
        小女孩在女廁場景中的顯示與點擊區。
        位置之後可以再微調。
        """
        return pygame.Rect(
            790,
            185,
            180,
            330
        )
    
    def should_show_girls_room_girl_after_fake_painting(self):
        """
        玩家取得肖像廳的第一幅《太陽之女》後，
        小女孩會重新出現在女廁，等待玩家交畫。
        """
        return (
            self.observation_scene_id == "girls_room"
            and self.story.has_girl_flag("fake_sunflower_painting_obtained")
            and not self.story.has_girl_flag("fake_sunflower_given_to_girl")
        )
    def should_show_history_room_girl(self):
        """
        館史室小女孩事件：
        - 謎語 1 已通關
        - 小女孩已移動到館史室
        - 謎語 2 尚未開始
        """
        return (
            self.observation_scene_id == "history_room"
            and self.story.has_girl_flag("girl_history_room_appeared")
            and not self.story.has_girl_flag("girl_riddle_2_started")
        )


    def get_history_room_girl_rect(self):
        """
        小女孩在館史室中的顯示與點擊區。
        位置可之後再微調。
        """
        return pygame.Rect(
            760,
            185,
            180,
            330
        )
    
    def should_show_special_hall_girl(self):
        """
        特展廳小女孩事件：
        - 謎語 2 已通關
        - 小女孩已移動到特展廳
        - 謎語 3 尚未開始
        """
        return (
            self.observation_scene_id == "special_hall"
            and self.story.has_girl_flag("girl_special_hall_appeared")
            and not self.story.has_girl_flag("girl_riddle_3_started")
        )

    def girl_gives_diary_event(self):
        """
        玩家交出肖像廳的第一幅《太陽之女》後：
        - 小女孩判斷不是她要找的那幅
        - 給玩家日記
        - 引導玩家根據日記尋找另一幅畫
        """
        self.active_item_id = None

        self.story.set_girl_flag("fake_sunflower_given_to_girl")
        self.story.set_girl_flag("girl_angry_and_kicked_player_out")
        self.story.set_girl_flag("diary_obtained")

        item = self.get_collectible_item("diary")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "小女孩把畫推了回來。",
            "她像是有些生氣，卻又像是早就知道你會找錯。",
            "她將一本邊角燒焦的日記丟到你面前。",
            "你獲得了【日記】。",
            "日記裡反覆寫著《太陽之女》的細節。",
            "也許你可以根據日記，再去倉庫找找看。"
        ])
    
    def get_special_hall_girl_rect(self):
        """
        小女孩在特展廳中的顯示與點擊區。
        """
        return pygame.Rect(
            760,
            185,
            180,
            330
        )
    # =========================================================
    # 館史室火災資料
    # =========================================================
    def should_show_history_fire_record(self):
        """
        館史室火災資料：
        - 謎語 2 已通關
        - 尚未讀過火災資料
        """
        return (
            self.observation_scene_id == "history_room"
            and self.story.has_girl_flag("girl_riddle_2_cleared")
            and not self.story.has_director_flag("fire_record_read")
        )

    def get_history_fire_record_rect(self):
        """
        館史室資料牆／展板互動區。
        位置之後可依圖片微調。
        """
        return pygame.Rect(
            470,
            165,
            330,
            210
        )

    def read_history_fire_record(self):
        """
        玩家閱讀館史室火災資料後：
        - 記錄火災資料已讀
        - 讓雕像館工友出現
        """
        self.story.set_director_flag("fire_record_read")
        self.story.set_director_flag("worker_spawned_in_sculpture_hall")

        self.start_message_reading([
            "牆上的館史資料記載著一場多年前的火災。",
            "火災後，美術館曾經歷過一次大規模改建。",
            "資料的最後一行被水痕暈開，只剩下幾個模糊的字。",
            "「……修復……工友……館長……」",
            "也許雕像館那邊，會有人知道些什麼。"
        ])
    # =========================================================
    # NPC：雕像館工友
    # =========================================================
    def should_show_sculpture_worker(self):
        """
        雕像館工友：
        - 玩家已讀過館史室火災資料
        - 工友已被允許出現
        - 工友姿勢題尚未開始
        """
        return (
            self.observation_scene_id == "sculpture_hall"
            and self.story.has_director_flag("worker_spawned_in_sculpture_hall")
            and not self.story.has_director_flag("worker_pose_question_started")
        )
    
    def should_show_sculpture_worker_light_bulb(self):
        """
        倉庫太暗後，玩家可以回雕像館找工友拿新燈泡。
        """
        return (
            self.observation_scene_id == "sculpture_hall"
            and self.story.has_director_flag("storage_darkness_seen")
            and not self.story.has_director_flag("light_bulb_obtained")
        )
    
    def get_storage_light_socket_rect(self):
        """
        倉庫燈座互動區。
        黑暗狀態下使用新燈泡點擊此處，可以讓倉庫亮燈。
        """
        return pygame.Rect(
            560,
            130,
            170,
            120
        )
    def try_install_light_bulb_in_storage(self):
        """
        使用新燈泡讓倉庫亮燈。
        """
        if self.story.has_director_flag("storage_light_on"):
            self.set_system_message("倉庫的燈已經亮了。")
            return

        if not self.story.has_director_flag("light_bulb_obtained"):
            self.set_system_message("太暗了，現在什麼也看不清楚。")
            return

        if self.active_item_id != "light_bulb":
            self.set_system_message("也許可以把工友給你的新燈泡裝上去。")
            return

        self.active_item_id = None
        self.remove_item_from_inventory("light_bulb")

        self.story.set_director_flag("light_bulb_installed")
        self.story.set_director_flag("storage_light_on")
        self.story.set_director_flag("storage_room_has_power")

        self.play_open_door_sound()

        self.start_message_reading([
            "你摸索著找到天花板下方的燈座。",
            "新燈泡旋入的瞬間，頭頂傳來微弱的電流聲。",
            "燈光閃爍了幾下，倉庫終於亮了起來。"
        ])
    def receive_light_bulb_event(self):
        """
        工友給玩家新燈泡。
        """
        self.story.set_director_flag("light_bulb_requested")
        self.story.set_director_flag("light_bulb_obtained")

        item = self.get_collectible_item("light_bulb")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "工友從工具箱裡翻出一顆新的燈泡。",
            "你獲得了【新燈泡】。",
            "也許現在可以回倉庫，把那裡照亮。"
        ])

    def get_sculpture_worker_rect(self):
        """
        工友在雕像館中的顯示與點擊區。
        位置可依圖片微調。
        """
        return pygame.Rect(
            770,
            175,
            190,
            340
        )

    def start_worker_pose_question_event(self):
        """
        工友初次對話結束後。
        """
        self.story.set_director_flag("worker_pose_question_started")
        self.puzzle.start_puzzle("worker_pose_question")
    # =========================================================
    # NPC：館長室館長
    # =========================================================
    def should_show_office_director(self):
        """
        館長室解鎖後，館長固定留在館長室。
        後續是否觸發任務，交由點擊館長時依照手上道具與劇情旗標判定。
        """
        return (
            self.observation_scene_id == "office"
            and self.story.has_director_flag("office_unlocked")
        )

    def get_office_director_rect(self):
        """
        館長在館長室中的顯示與點擊區。
        位置之後可依 Office.png 微調。
        """
        return pygame.Rect(
            760,
            165,
            200,
            350
        )    
    def receive_color_mixing_task_event(self):
        """
        館長初次對話結束後：
        - 接取修復室調色任務
        - 取得色票
        - 引導玩家前往修復室
        """
        self.story.set_director_flag("color_mixing_task_received")
        self.story.set_director_flag("color_ticket_obtained")

        item = self.get_collectible_item("color_ticket")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "館長交給你一張褪色的色票。",
            "你獲得了【色票】。",
            "他要你去修復室，依照色票調出正確的顏色。",
            "也許修復室裡會有可以使用的材料。"
        ])
    # =========================================================
    # 觀察畫面滑鼠點擊
    # =========================================================
    def handle_observation_click(self, mouse_pos):

        # ==================================================
        # 結局 DEBUG：出口出現後，點擊男廁任意位置觸發結局
        # ==================================================
        if (
            self.observation_scene_id == "boys_room"
            and self.true_exit_found
        ):
            self.start_ending_event()
            return

        # ==================================================
        # 遮色片：使用後在男廁點擊任意位置，讓出口出現
        # ==================================================
        if (
            self.observation_scene_id == "boys_room"
            and self.active_item_id == "color_filter"
        ):
            self.inspect_boys_room_exit_with_filter()
            return
        # ==================================================
        # 黑暗倉庫：尚未開燈前只能嘗試裝燈泡
        # ==================================================
        if (
            self.observation_scene_id == "storage_room"
            and not self.story.has_director_flag("storage_light_on")
        ):
            light_socket_rect = self.get_storage_light_socket_rect()

            if light_socket_rect.collidepoint(mouse_pos):
                self.try_install_light_bulb_in_storage()
            else:
                self.set_system_message("太暗了，現在什麼也看不清楚。")

            return
        # ==================================================
        # 謎題選項點擊
        # ==================================================
        if self.puzzle.is_active():
            if self.handle_puzzle_choice_click(mouse_pos):
                return
            
        # ==================================================
        # 工友第二階段：指出雕像左手異常
        # ==================================================
        if self.should_show_worker_statue_spot_task():
            left_hand_rect = self.get_worker_statue_left_hand_rect()

            if left_hand_rect.collidepoint(mouse_pos):
                self.complete_worker_statue_spot_task()
                return

        # ==================================================
        # 館史室火災資料
        # ==================================================
        if self.should_show_history_fire_record():
            fire_record_rect = self.get_history_fire_record_rect()

            if fire_record_rect.collidepoint(mouse_pos):
                self.read_history_fire_record()
                return
            
       # ==================================================
        # 雕像館工友 NPC
        # ==================================================
        if (
            self.should_show_sculpture_worker()
            or self.should_show_sculpture_worker_light_bulb()
        ):
            worker_rect = self.get_sculpture_worker_rect()

            if worker_rect.collidepoint(mouse_pos):
                if self.should_show_sculpture_worker_light_bulb():
                    self.start_dialogue("worker_light_bulb_intro")
                else:
                    self.start_dialogue("worker_sculpture_intro")

                return
        # ==================================================
        # 館長室保險箱
        # ==================================================
        if self.observation_scene_id == "office":
            safe_rect = self.get_office_safe_rect()

            if safe_rect.collidepoint(mouse_pos):
                self.try_use_unknown_key_on_office_safe()
                return

        # ==================================================
        # 館長室館長 NPC
        # ==================================================
        if self.should_show_office_director():
            director_rect = self.get_office_director_rect()

            if director_rect.collidepoint(mouse_pos):
                print("[DEBUG] active_item_id when clicking director:", self.active_item_id)
                # ==================================================
                # 最終真相：
                # 使用【拼好的照片】點擊館長
                # ==================================================
                if self.active_item_id == "photo_complete":
                    self.story.set_director_flag("director_final_truth_started")
                    self.active_item_id = None
                    self.start_dialogue("director_final_truth")
                    return

                # ==================================================
                # 已經拼好照片，但玩家還沒拿出照片
                # ==================================================
                if (
                    self.story.has_girl_flag("girl_route_finished")
                    and self.story.has_main_flag("photo_completed")
                    and not self.story.has_director_flag("director_final_truth_started")
                ):
                    self.set_system_message("也許該把拼好的照片拿出來，讓館長看看。")
                    return

                # ==================================================
                # 第一次見館長：接調色任務
                # ==================================================
                if not self.story.has_director_flag("color_mixing_task_received"):
                    self.start_dialogue("director_office_intro")
                    return

                # ==================================================
                # 回報調色盤：
                # 必須先從口袋使用【調色盤】
                # ==================================================
                if (
                    self.story.has_director_flag("color_done_obtained")
                    and not self.story.has_director_flag("special_key_obtained")
                ):
                    if self.active_item_id == "color_done":
                        self.start_dialogue("director_color_done_report")
                    else:
                        self.start_dialogue("director_idle")

                    return

                # ==================================================
                # 回報算出的色碼：
                # 必須先從口袋使用【算出的色碼】
                # 答對後會直接取得未知鑰匙
                # ==================================================
                if (
                    self.story.has_director_flag("calculated_color_codes_obtained")
                    and not self.story.has_director_flag("unknown_key_obtained")
                ):
                    if self.active_item_id == "calculated_color_codes":
                        self.start_dialogue("director_color_code_report")
                    else:
                        self.start_dialogue("director_idle")

                    return

                # ==================================================
                # 沒有可回報內容
                # ==================================================
                self.start_dialogue("director_idle")
                return
        # ==================================================
        # 女廁小女孩 NPC
        # ==================================================
        if (
            self.should_show_girls_room_girl()
            or self.should_show_girls_room_girl_after_fake_painting()
            or self.should_show_girls_room_girl_after_high_quality_painting()
            or self.should_show_girls_room_girl_after_true_painting()
        ):
            girl_rect = self.get_girls_room_girl_rect()

            if girl_rect.collidepoint(mouse_pos):
                current_sunflower = self.get_collectible_item_by_name("太陽之女")
                current_sunflower_id = None

                if current_sunflower:
                    current_sunflower_id = current_sunflower["id"]

                if self.should_show_girls_room_girl_after_true_painting():
                    if self.active_item_id == "true_sunflower_painting":
                        self.start_dialogue("girl_receive_true_sunflower")
                    else:
                        self.set_system_message("她似乎在等你把真正的《太陽之女》拿出來。")

                elif self.should_show_girls_room_girl_after_high_quality_painting():
                    if self.active_item_id == "high_quality_fake_sunflower":
                        self.start_dialogue("girl_receive_high_quality_sunflower")
                    else:
                        self.set_system_message("她似乎在等你把另一幅《太陽之女》拿出來。")

                elif self.should_show_girls_room_girl_after_fake_painting():
                    if self.active_item_id == "fake_sunflower_painting":
                        self.start_dialogue("girl_receive_fake_sunflower")
                    else:
                        self.set_system_message("她似乎在等你把找到的《太陽之女》拿出來。")

                else:
                    self.start_dialogue("girl_girls_room_intro")

                return
        # ==================================================
        # 館史室小女孩 NPC
        # ==================================================
        if self.should_show_history_room_girl():
            girl_rect = self.get_history_room_girl_rect()

            if girl_rect.collidepoint(mouse_pos):
                self.start_dialogue("girl_history_room_intro")
                return
        # ==================================================
        # 特展廳小女孩 NPC
        # ==================================================
        if self.should_show_special_hall_girl():
            girl_rect = self.get_special_hall_girl_rect()

            if girl_rect.collidepoint(mouse_pos):
                self.start_dialogue("girl_special_hall_intro")
                return
        # ==================================================
        # 男廁小女孩 NPC
        # ==================================================
        if self.should_show_boys_room_girl_after_riddle_4():
            girl_rect = self.get_boys_room_girl_rect()

            if girl_rect.collidepoint(mouse_pos):
                self.start_dialogue("girl_boys_room_truth_hint")
                return
        # ==================================================
        # 男廁出口：遮色片
        # ==================================================
        if self.observation_scene_id == "boys_room":
            exit_rect = self.get_boys_room_exit_rect()

            if exit_rect.collidepoint(mouse_pos):
                self.inspect_boys_room_exit_with_filter()
                return
        # ==================================================
        # 修復室：真正的《太陽之女》
        # ==================================================
        if self.observation_scene_id == "fix_room":
            true_painting_rect = self.get_fix_room_true_painting_rect()

            if true_painting_rect.collidepoint(mouse_pos):
                self.inspect_fix_room_true_painting()
                return
        # ==================================================
        # 特展廳：使用色碼題紙開始色碼運算
        # ==================================================
        if self.observation_scene_id == "special_hall":
            color_wall_rect = self.get_special_hall_color_wall_rect()

            if color_wall_rect.collidepoint(mouse_pos):
                self.try_use_color_code_note_on_special_wall()
                return
        # ==================================================
        # 可拾取道具
        # ==================================================
        collectible_item = self.get_collectible_item_at_pos(
            self.observation_scene_id,
            mouse_pos
        )

        if collectible_item:
            self.start_item_preview(collectible_item["id"])
            return
        # ==================================================
        # 修復室：使用色票開始調色關卡
        # ==================================================
        if self.observation_scene_id == "fix_room":
            color_table_rect = self.get_fix_room_color_table_rect()

            if color_table_rect.collidepoint(mouse_pos):
                self.try_use_color_ticket_on_fix_table()
                return
        # ==================================================
        # 修復室 → 倉庫互動區
        # ==================================================
        if self.observation_scene_id == "fix_room":
            storage_hotspot = self.get_fix_room_storage_hotspot_rect()

            if storage_hotspot.collidepoint(mouse_pos):
                self.try_enter_observation_room(
                    scene_id="storage_room",
                    location_name="倉庫",
                    return_mode="observation",
                    return_scene_id="fix_room",
                    return_location_name="修復室"
                )
        # ==================================================
        # 亮燈倉庫：左下黑箱與畫作調查
        # ==================================================
        if (
            self.observation_scene_id == "storage_room"
            and self.story.has_director_flag("storage_light_on")
        ):
            newspaper_box_rect = self.get_storage_newspaper_box_rect()

            if newspaper_box_rect.collidepoint(mouse_pos):
                self.inspect_storage_newspaper_box()
                return

            for painting_data in self.get_storage_painting_rects():
                if painting_data["rect"].collidepoint(mouse_pos):
                    self.inspect_storage_painting(painting_data)
                    return
                
    def try_use_color_code_note_on_special_wall(self):
        """
        玩家在特展廳使用色碼題紙後，啟動三題色碼運算。
        """
        if not self.story.has_director_flag("special_hall_task_received"):
            self.set_system_message("牆上排列著幾組色塊，但你還不知道該怎麼解讀。")
            return

        if self.story.has_director_flag("special_hall_color_code_cleared"):
            self.set_system_message("你已經算出特展廳的色碼了。")
            return

        if self.active_item_id != "color_code_note":
            self.set_system_message("也許需要拿出館長給你的色碼題紙來對照。")
            return

        self.active_item_id = None
        self.remove_item_from_inventory("color_code_note")
        self.story.set_director_flag("special_hall_color_code_started")

        self.set_system_message(
            "你將色碼題紙貼近展示牆，牆上的色塊開始錯位。"
        )

        self.start_mutated_room(
            "special_hall",
            sanity_decay_per_second=1.2
        )

        self.puzzle.start_puzzle("special_hall_color_code_1")    
    # =========================================================
    # 謎題通關處理
    # =========================================================
    def handle_puzzle_clear_action(self, action):
        if action == "clear_girl_riddle_1":
            self.clear_girl_riddle_1_event()

        elif action == "clear_girl_riddle_2":
            self.clear_girl_riddle_2_event()

        elif action == "clear_worker_pose_question":
            self.clear_worker_pose_question_event()

        elif action == "clear_fix_room_color_mixing_1":
            self.clear_fix_room_color_mixing_1_event()

        elif action == "clear_fix_room_color_mixing_2":
            self.clear_fix_room_color_mixing_2_event()

        elif action == "clear_fix_room_color_mixing_3":
            self.clear_fix_room_color_mixing_3_event()

        elif action == "clear_special_hall_color_code_1":
            self.clear_special_hall_color_code_1_event()

        elif action == "clear_special_hall_color_code_2":
            self.clear_special_hall_color_code_2_event()

        elif action == "clear_special_hall_color_code_3":
            self.clear_special_hall_color_code_3_event()

        elif action == "clear_director_color_code_report":
            self.clear_director_color_code_report_event()

        elif action == "clear_director_reasoning_1":
            self.clear_director_reasoning_1_event()

        elif action == "clear_girl_riddle_3":
            self.clear_girl_riddle_3_event()
        
        elif action == "clear_girl_riddle_4":
            self.clear_girl_riddle_4_event()
    
    
    def clear_girl_riddle_1_event(self):
        """
        謎語 1 解開後：
        - 記錄通關
        - 解除變異女廁
        - 開啟小女孩下一階段：館史室
        """

        self.story.set_main_flag("girl_riddle_1_cleared")
        self.story.set_girl_flag("girl_history_room_appeared")

        self.clear_mutated_room("girls_room")

        self.start_message_reading([
            "女廁恢復了原本的樣子。",
            "小女孩已經不見了。",
            "也許你該去別的地方找她。"
        ])
    def clear_girl_riddle_2_event(self):
        """
        謎語 2 解開後：
        - 記錄通關
        - 解除變異館史室
        - 開啟小女孩下一階段：特展廳
        """

        self.story.set_girl_flag("girl_riddle_2_cleared")
        self.story.set_girl_flag("girl_special_hall_appeared")

        self.clear_mutated_room("history_room")

        self.start_message_reading([
            "館史室恢復了安靜。",
            "小女孩又不見了。",
            "她剛才提到，館裡還有其他人。",
            "也許館史室裡還留著能解釋這一切的資料。"
        ])
    def clear_worker_pose_question_event(self):
        """
        工友姿勢題答對後：
        - 記錄第一階段完成
        - 開啟第二階段：指出雕像左手異常
        """
        self.story.set_director_flag("worker_pose_question_cleared")
        self.story.set_director_flag("worker_statue_spot_started")

        self.start_message_reading([
            "工友點了點頭。",
            "「還行，至少看得出人物重心。」",
            "「那你再看看，中間那尊雕像有什麼不對勁？」",
            "「把有問題的地方指出來給我看。」"
        ])
    def clear_director_reasoning_1_event(self):
        """
        館長推理 1 解開後：
        - 解除館長室變異
        - 取得未知鑰匙
        """
        self.story.set_director_flag("director_reasoning_1_cleared")
        self.story.set_director_flag("unknown_key_obtained")

        self.clear_mutated_room("office")

        item = self.get_collectible_item("unknown_key")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "館長沉默了一會兒。",
            "「有些空間，不是被遺忘了。」",
            "「只是不能被太早發現。」",
            "他將一把用途不明的鑰匙交給你。",
            "你獲得了【未知的鑰匙】。"
        ])
    def try_use_color_ticket_on_fix_table(self):
        """
        玩家在修復室桌子使用色票後，啟動三題調色關卡。
        """
        if not self.story.has_director_flag("color_mixing_task_received"):
            self.set_system_message("桌上散落著顏料，但你還不知道要調出什麼顏色。")
            return

        if self.story.has_director_flag("color_mixing_task_cleared"):
            self.set_system_message("你已經完成調色了。")
            return

        if self.active_item_id != "color_ticket":
            self.set_system_message("也許需要拿出館長給你的色票來對照。")
            return

        self.active_item_id = None
        self.remove_item_from_inventory("color_ticket")
        self.story.set_director_flag("color_mixing_task_started")

        self.set_system_message(
            "你將色票放在桌上，開始比對顏料。"
        )

        self.start_mutated_room(
            "fix_room",
            sanity_decay_per_second=1.2
        )

        self.puzzle.start_puzzle("fix_room_color_mixing_1")
    def clear_fix_room_color_mixing_event(self):
        """
        修復室調色題完成：
        - 解除變異修復室
        - 取得正確的顏色
        - 可回館長室交差
        """
        self.story.set_director_flag("color_mixing_task_cleared")
        self.story.set_director_flag("correct_color_obtained")

        self.clear_mutated_room("fix_room")

        item = self.get_collectible_item("correct_color")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "顏料逐漸穩定下來。",
            "你調出了接近色票的顏色。",
            "你獲得了【正確的顏色】。",
            "也許該回館長室向館長報告。"
        ])
    def should_show_worker_statue_spot_task(self):
        return (
            self.observation_scene_id == "sculpture_hall"
            and self.story.has_director_flag("worker_statue_spot_started")
            and not self.story.has_director_flag("worker_statue_spot_cleared")
        )


    def get_worker_statue_left_hand_rect(self):
        return pygame.Rect(
            590,
            235,
            35,
            60
        )

    def clear_special_hall_color_code_1_event(self):
        self.story.set_director_flag("special_hall_color_code_1_cleared")
        self.set_system_message("第一組色碼完成。")
        self.puzzle.start_puzzle("special_hall_color_code_2")


    def clear_special_hall_color_code_2_event(self):
        self.story.set_director_flag("special_hall_color_code_2_cleared")
        self.set_system_message("第二組色碼完成。")
        self.puzzle.start_puzzle("special_hall_color_code_3")


    def clear_special_hall_color_code_3_event(self):
        self.story.set_director_flag("special_hall_color_code_3_cleared")
        self.story.set_director_flag("special_hall_color_code_cleared")
        self.story.set_director_flag("calculated_color_codes_obtained")

        self.clear_mutated_room("special_hall")

        item = self.get_collectible_item("calculated_color_codes")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "第三組色碼也穩定了下來。",
            "你把三組運算結果記錄在紙上。",
            "你獲得了【算出的色碼】。",
            "也許該回館長室向館長報告。"
        ])
    def clear_director_color_code_report_event(self):
        """
        館長確認色碼判讀後：
        - 不再取得「正確的色碼」
        - 直接取得未知的鑰匙
        """
        self.story.set_director_flag("director_color_code_report_cleared")
        self.story.set_director_flag("unknown_key_obtained")

        item = self.get_collectible_item("unknown_key")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.active_item_id = None

        self.start_message_reading([
            "館長沉默地看著你寫下的答案。",
            "「深藍、深咖啡、淺墨綠……」",
            "「沒錯，這就是那組色碼真正指向的顏色。」",
            "他將一把用途不明的鑰匙交給你。",
            "你獲得了【未知的鑰匙】。"
    ])
    def complete_worker_statue_spot_task(self):
        self.story.set_director_flag("worker_statue_spot_cleared")
        self.story.set_director_flag("office_key_obtained")

        item = self.get_collectible_item("office_key")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "工友瞇起眼看了看你指出的位置。",
            "「對，就是那隻手。」",
            "「它不是左手，是多出來的右手。」",
            "「這種錯誤不該出現在正式展品上。」",
            "工友把一把鑰匙交到你手上。",
            "你獲得了【館長室鑰匙】。",
            "「去找館長吧。他應該知道為什麼會變成這樣。」"
        ])
    def try_start_fix_room_color_mixing_event(self):
        """
        接到館長調色任務後，第一次進入修復室：
        - 修復室變異
        - 啟動調色題
        """
        if not self.story.has_director_flag("color_mixing_task_received"):
            return

        if self.story.has_director_flag("color_mixing_task_cleared"):
            return

        if self.story.has_director_flag("color_mixing_task_started"):
            return

        self.story.set_director_flag("color_mixing_task_started")

        self.set_system_message(
            "修復室裡的顏料氣味忽然變得刺鼻，牆上的畫框開始微微震動。"
        )

        self.start_mutated_room(
            "fix_room",
            sanity_decay_per_second=1.2
        )

        self.puzzle.start_puzzle("fix_room_color_mixing")
    # =========================================================
    # 主迴圈
    # =========================================================
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            mouse_pos = pygame.mouse.get_pos()
            mouse_down = False
            keys = pygame.key.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                # ==================================================
                # 暫停選單開啟時，只處理暫停選單相關操作
                # ==================================================
                if self.pause_menu_open:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_p:
                            self.close_pause_menu()
                        continue


                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self.get_bgm_slider_rect().collidepoint(event.pos):
                            self.dragging_bgm_slider = True
                            self.update_bgm_volume_from_mouse(event.pos[0])
                            continue

                        if self.get_brightness_slider_rect().collidepoint(event.pos):
                            self.dragging_brightness_slider = True
                            self.update_brightness_from_mouse(event.pos[0])
                            continue

                        if self.get_resume_button_rect().collidepoint(event.pos):
                            self.close_pause_menu()
                            continue

                        if self.get_return_menu_button_rect().collidepoint(event.pos):
                            self.return_to_main_menu()
                            continue

                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        self.dragging_bgm_slider = False
                        self.dragging_brightness_slider = False
                        continue

                    continue

                # ==================================================
                # 正常遊戲狀態：鍵盤事件
                # ==================================================
                if event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        continue

                    # P：開啟暫停選單
                    if event.key == pygame.K_p:
                        self.toggle_pause_menu()
                        continue

                    # unlock 碎片預覽狀態中，Space 收下碎片
                    if self.mode == "fragment_preview":
                        if event.key == pygame.K_SPACE:
                            self.close_fragment_preview()
                        continue

                    # NPC 對話狀態中，Space 推進對話
                    if self.mode == "dialogue":
                        if event.key == pygame.K_SPACE:
                            self.advance_dialogue()
                        continue

                    # 道具預覽狀態中，Space 收入口袋
                    if self.mode == "item_preview":
                        if event.key == pygame.K_SPACE:
                            self.collect_preview_item()
                        continue

                    # 訊息讀取狀態中，只接受 Space 推進訊息
                    if self.message_reading:
                        if event.key == pygame.K_SPACE:
                            self.advance_message_reading()
                        continue

                    # Q：開關口袋
                    if event.key == pygame.K_q and self.mode in ["hallway", "observation"]:
                        self.toggle_pocket()
                        continue

                    # E：走廊移動區域互動
                    if event.key == pygame.K_e and self.mode == "hallway":
                        if not self.pocket_open:
                            self.try_move_in_hallway()
                        continue

                    # E：觀察狀態返回
                    if event.key == pygame.K_e and self.mode == "observation":
                        if not self.pocket_open:
                            self.return_from_observation()
                        continue

                # ==================================================
                # 正常遊戲狀態：滑鼠事件
                # ==================================================
                if event.type == pygame.MOUSEWHEEL:
                    if self.pocket_open:
                        self.scroll_pocket(-event.y)
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.mode == "dialogue":
                        self.handle_dialogue_choice_click(event.pos)
                        continue

                    mouse_down = True

            # ==================================================
            # 暫停選單拖曳滑桿
            # ==================================================
            if self.pause_menu_open:
                if self.dragging_bgm_slider:
                    self.update_bgm_volume_from_mouse(mouse_pos[0])

                if self.dragging_brightness_slider:
                    self.update_brightness_from_mouse(mouse_pos[0])

            # ==================================================
            # 暫停狀態：保留原畫面，但不更新遊戲邏輯
            # ==================================================
            if self.pause_menu_open:
                if self.mode == "hallway":
                    self.renderer.draw_hallway()

                elif self.mode == "observation":
                    self.renderer.draw_observation()

                self.apply_brightness_overlay()
                self.renderer.draw_pause_menu()
                pygame.display.flip()
                continue

            if not self.pause_menu_open:
                self.update_mutation_system(dt)

            # ==================================================
            # 正常遊戲畫面更新
            # ==================================================
            if self.mode == "menu":
                self.renderer.draw_menu(mouse_pos, mouse_down)

            elif self.mode == "hallway":
                self.update_game_time()

                if not self.pocket_open and not self.message_reading:
                    self.hallway.update(keys)

                if mouse_down and self.pocket_open and not self.message_reading:
                    self.handle_pocket_click(mouse_pos)

                self.update_walk_sound()
                self.renderer.draw_hallway()

            elif self.mode == "observation":
                self.update_game_time()

                if mouse_down and not self.message_reading:
                    if self.pocket_open:
                        self.handle_pocket_click(mouse_pos)
                    else:
                        self.handle_observation_click(mouse_pos)

                self.update_walk_sound()
                self.renderer.draw_observation()

            elif self.mode == "item_preview":
                self.update_game_time()
                self.renderer.draw_item_preview()

            elif self.mode == "fragment_preview":
                self.update_game_time()
                self.renderer.draw_fragment_preview()

            elif self.mode == "dialogue":
                self.update_game_time()
                self.renderer.draw_dialogue()

            self.apply_brightness_overlay()
            self.apply_screen_shake()
            pygame.display.flip()

        pygame.quit()
        sys.exit()
    # =========================================================
    # 暫停選單區域
    # =========================================================
    def get_pause_panel_rect(self):
        panel_width = 720
        panel_height = 500
        panel_x = WIDTH // 2 - panel_width // 2
        panel_y = HEIGHT // 2 - panel_height // 2

        return pygame.Rect(
            panel_x,
            panel_y,
            panel_width,
            panel_height
        )

    def get_bgm_slider_rect(self):
        panel = self.get_pause_panel_rect()

        return pygame.Rect(
            panel.x + 230,
            panel.y + 145,
            330,
            12
        )

    def get_brightness_slider_rect(self):
        panel = self.get_pause_panel_rect()

        return pygame.Rect(
            panel.x + 230,
            panel.y + 235,
            330,
            12
        )

    def get_resume_button_rect(self):
        panel = self.get_pause_panel_rect()

        return pygame.Rect(
            panel.centerx - 130,
            panel.y + 335,
            260,
            54
        )

    def get_return_menu_button_rect(self):
        panel = self.get_pause_panel_rect()

        return pygame.Rect(
            panel.centerx - 130,
            panel.y + 405,
            260,
            54
        )
    
    # =========================================================
    # 暫停選單邏輯
    # =========================================================
    def can_open_pause_menu(self):
        return (
            self.mode in ["hallway", "observation"]
            and not self.message_reading
            and not self.pocket_open
        )

    def open_pause_menu(self):
        if not self.can_open_pause_menu():
            return

        self.pause_menu_open = True
        self.stop_walk_sound()
        self.pause_game_time()

    def close_pause_menu(self):
        self.pause_menu_open = False
        self.dragging_bgm_slider = False
        self.dragging_brightness_slider = False
        self.resume_game_time()

    def toggle_pause_menu(self):
        if self.pause_menu_open:
            self.close_pause_menu()
        else:
            self.open_pause_menu()

    def return_to_main_menu(self):
        self.pause_menu_open = False
        self.dragging_bgm_slider = False
        self.dragging_brightness_slider = False

        self.stop_walk_sound()
        pygame.mixer.music.stop()

        self.mode = "menu"

        # 避免維持在暫停狀態
        self.time_paused = False
        self.pause_started_at = None

    def update_bgm_volume_from_mouse(self, mouse_x):
        slider = self.get_bgm_slider_rect()

        ratio = (mouse_x - slider.x) / slider.width
        ratio = max(0.0, min(1.0, ratio))

        self.bgm_volume_ratio = ratio

        pygame.mixer.music.set_volume(
            self.bgm_max_volume * self.bgm_volume_ratio
        )

    def update_brightness_from_mouse(self, mouse_x):
        slider = self.get_brightness_slider_rect()

        ratio = (mouse_x - slider.x) / slider.width
        ratio = max(0.0, min(1.0, ratio))

        self.screen_brightness = ratio
    # =========================================================
    # 口袋系統
    # =========================================================
    def toggle_pocket(self):
        self.pocket_open = not self.pocket_open
        self.stop_walk_sound()

        if self.pocket_open:
            # 每次重新打開口袋，先不預設選道具
            self.pocket_inspected_item_id = None
            self.pocket_scroll_index = 0
            self.set_system_message("你打開了口袋。")
        else:
            self.set_system_message("你收起了口袋。")

    def scroll_pocket(self, direction):
        """
        口袋左側道具清單滾動。
        direction: -1 往上，1 往下。
        """
        if not self.pocket_open:
            return

        max_index = max(
            0,
            len(self.inventory.items) - self.pocket_visible_count
        )

        self.pocket_scroll_index += direction
        self.pocket_scroll_index = max(
            0,
            min(self.pocket_scroll_index, max_index)
        )

    def get_pocket_item_rects(self):
        panel_rect = self.get_pocket_panel_rect()

        item_x = panel_rect.x + 40
        item_y = panel_rect.y + 105
        item_width = 360
        item_height = 52
        item_gap = 8

        rects = []

        visible_items = self.inventory.items[
            self.pocket_scroll_index:
            self.pocket_scroll_index + self.pocket_visible_count
        ]

        for i, item_name in enumerate(visible_items):
            rect = pygame.Rect(
                item_x,
                item_y + i * (item_height + item_gap),
                item_width,
                item_height
            )

            rects.append((item_name, rect))

        return rects

    def get_pocket_use_button_rect(self):
        panel_rect = self.get_pocket_panel_rect()

        button_width = 130
        button_height = 42

        # 右側資訊卡區域大致從 panel_rect.x + 430 開始
        info_area_left = panel_rect.x + 430
        info_area_width = panel_rect.width - 430

        button_x = info_area_left + info_area_width // 2 - button_width // 2
        button_y = panel_rect.bottom - 65

        return pygame.Rect(
            button_x,
            button_y,
            button_width,
            button_height
        )
    def handle_pocket_click(self, mouse_pos):
    # 1. 若已經選到某個道具，先判斷是否點到【使用】
        if self.pocket_inspected_item_id is not None:
            use_button_rect = self.get_pocket_use_button_rect()

            if use_button_rect.collidepoint(mouse_pos):
                self.use_pocket_item(self.pocket_inspected_item_id)
                return True

        # 2. 點左側清單中的道具 → 顯示右側資訊欄
        for item_name, rect in self.get_pocket_item_rects():
            if rect.collidepoint(mouse_pos):
                item_data = self.get_collectible_item_by_name(item_name)

                if item_data:
                    self.pocket_inspected_item_id = item_data["id"]

                return True

        return False
    
    def get_pocket_panel_rect(self):
        panel_width = 980
        panel_height = 420
        panel_x = WIDTH // 2 - panel_width // 2
        panel_y = HEIGHT // 2 - panel_height // 2

        return pygame.Rect(
            panel_x,
            panel_y,
            panel_width,
            panel_height
        )
    def use_pocket_item(self, item_id):
        item = self.get_collectible_item(item_id)

        if item is None:
            return

        if not item["collected"]:
            return

        self.pocket_open = False
        self.pocket_inspected_item_id = None

        # ==================================================
        # 日記：閱讀內容，不作為場景使用道具
        # ==================================================
        if item_id == "diary":
            self.active_item_id = None

            self.start_message_reading([
                "你翻開那本邊角燒焦的日記。",
                "裡面反覆記著一幅名為《太陽之女》的畫。",
                "日記寫著：畫中的女孩站在昏暗的背景前，身上像覆著一層細碎的光。",
                "她的輪廓不是被線條勾出來的，而像是從黑暗裡慢慢亮起來。",
                "那份光很柔和，卻讓人無法把視線移開。",
                "最後一頁的字跡被水痕暈開，只看得出幾句：",
                "「那幅畫後來被拿去修了。」",
                "「他們說只是普通修復，可是回來之後，好像就不是原本那幅了。」"
            ])
            return
        if item_id == "newspaper_clipping":
            self.active_item_id = None

            self.start_message_reading([
                "你攤開那份泛黃的舊報紙。",
                "紙面上還留著火災後的焦痕，有些字已經模糊不清。",
                "你勉強讀出幾段殘缺的內容：",
                "「……美術館火災……」",
                "「……展間改建……」",
                "「……館長聲明……」",
                "「……女童……畫作……未尋獲……」",
                "報紙的角落還寫著一行小字：事故後，部分展品被送往修復室重新處理。"
            ])
            return

        self.active_item_id = item_id

        self.set_system_message(
            f"你拿出了「{item['name']}」。"
        )
    # =========================================================
    # 房間狀態系統
    # =========================================================
    def reset_room_states(self):
        self.room_states = {
            "storage_room": {
                "locked": True,
                "unlock_condition": None
            },
            "office": {
                "locked": True,
                "unlock_condition": None
            },
            "girls_room": {
                "locked": True,
                "unlock_condition": None
            },
            "special_hall": {
                "locked": True,
                "unlock_condition": None
            },
            "portraits_hall": {
                "locked": True,
                "unlock_condition": None
            },
        }

    def is_room_locked(self, scene_id):
        room_state = self.room_states.get(scene_id)

        if room_state is None:
            return False

        return room_state["locked"]

    def unlock_room(self, scene_id):
        if scene_id in self.room_states:
            self.room_states[scene_id]["locked"] = False

    def show_locked_room_message(self):
        self.stop_walk_sound()
        self.play_lock_sound()
        self.start_screen_shake()

        self.set_system_message(
            "似乎上鎖了，得找到鑰匙或是想別的辦法了。"
        )

    def try_use_active_item_on_locked_room(self, scene_id, location_name):
        """
        判斷目前手上的道具，是否能解開這扇上鎖的門。

        成功時：
        - 將房間改為未上鎖
        - 清除目前手持道具
        - 顯示開鎖劇情訊息
        - 不直接進入房間，玩家需第二次按 E
        """

        # 廁所鑰匙 → 打開女廁
        if (
            self.active_item_id == "toilet_key"
            and scene_id == "girls_room"
        ):
            self.unlock_room("girls_room")
            self.active_item_id = None

            # ==================================================
            # 主線進度：女廁解鎖、取得第一片 unlock 碎片
            # ==================================================
            self.story.set_main_flag("girls_room_unlocked")
            self.story.obtain_fragment("girls_room")
            self.story.set_main_flag("fragment_from_girls_room_obtained")

            self.play_open_door_sound()

            self.start_fragment_preview(
                fragment_id="girls_room",
                title="照片一角",
                description="「咖」的一聲，門打開了。一塊形狀奇特的碎片，從門鎖旁掉了下來。"
            )

            return True
                # 館長室鑰匙 → 打開館長室
        if (
            self.active_item_id == "office_key"
            and scene_id == "office"
        ):
            self.unlock_room("office")
            self.active_item_id = None

            # ==================================================
            # 支線二進度：館長室解鎖、取得第二片 unlock 碎片
            # ==================================================
            self.story.set_director_flag("office_unlocked")
            self.story.obtain_fragment("office")
            self.story.set_director_flag("fragment_from_office_obtained")

            self.play_open_door_sound()

            self.start_fragment_preview(
                fragment_id="office",
                title="照片一角",
                description="門鎖鬆開的瞬間，一塊新的碎片從門縫中掉了出來。"
            )

            return True
            # 特展廳鑰匙 → 打開特展廳
        if (
            self.active_item_id == "special_key"
            and scene_id == "special_hall"
        ):
            self.unlock_room("special_hall")
            self.active_item_id = None

            self.story.set_director_flag("special_hall_unlocked")
            self.story.obtain_fragment("special_hall")
            self.story.set_director_flag("fragment_from_special_hall_obtained")

            self.play_open_door_sound()

            self.start_fragment_preview(
                fragment_id="special_hall",
                title="照片一角",
                description="特展廳的門鎖鬆開後，一塊碎片從展示牌後方滑落。"
            )

            return True

        # 肖像館鑰匙 → 打開肖像展廳
        if (
            self.active_item_id == "portrait_key"
            and scene_id == "portraits_hall"
        ):
            self.unlock_room("portraits_hall")
            self.active_item_id = None

            self.story.set_girl_flag("portraits_hall_unlocked_by_girl")
            self.story.set_girl_flag("fragment_from_portraits_hall_obtained")
            self.story.obtain_fragment("portraits_hall")

            self.play_open_door_sound()

            self.start_fragment_preview(
                fragment_id="portraits_hall",
                title="照片一角",
                description="肖像展廳的門鎖鬆開後，一片照片碎片從門縫中掉了下來。"
            )

            return True
        
        # 倉庫鑰匙 → 打開倉庫
        if (
            self.active_item_id == "storage_key"
            and scene_id == "storage_room"
        ):
            self.unlock_room("storage_room")
            self.active_item_id = None

            self.story.set_director_flag("storage_room_unlocked")
            self.story.obtain_fragment("storage_room")
            self.story.set_director_flag("fragment_from_storage_room_obtained")

            self.play_open_door_sound()

            self.start_fragment_preview(
                fragment_id="storage_room",
                title="照片一角",
                description="倉庫門被打開後，一片照片碎片從門縫邊掉了下來。"
            )

            return True
        return False
    
    def try_enter_observation_room(
        self,
        scene_id,
        location_name,
        return_mode="hallway",
        return_area_id=None,
        return_spawn_x=None,
        return_scene_id=None,
        return_location_name=None
    ):
        if self.is_room_locked(scene_id):
            unlocked_by_item = self.try_use_active_item_on_locked_room(
                scene_id,
                location_name
            )

            # 有成功用道具開鎖：
            # 這一次只開鎖，不進入房間
            if unlocked_by_item:
                return False

            # 沒有正確道具，維持鎖門狀態
            self.show_locked_room_message()
            return False

        self.stop_walk_sound()
        self.play_open_door_sound()

        self.start_observation(
            scene_id=scene_id,
            location_name=location_name,
            return_mode=return_mode,
            return_area_id=return_area_id,
            return_spawn_x=return_spawn_x,
            return_scene_id=return_scene_id,
            return_location_name=return_location_name
        )

        return True
    def get_special_hall_color_wall_rect(self):
        """
        特展廳色碼展示牆互動區。
        玩家使用色碼題紙後，點擊這裡開始色碼運算。
        """
        return pygame.Rect(
            430,
            150,
            420,
            260
        )

    def get_office_safe_rect(self):
        """
        館長室保險箱互動區。
        """
        return pygame.Rect(
            270,
            275,
            85,
            90
        )

    def should_show_office_safe(self):
        """
        館長推理 1 通關後，保險箱成為可互動物件。
        """
        return (
            self.observation_scene_id == "office"
            and self.story.has_director_flag("unknown_key_obtained")
            and not self.is_collectible_collected("storage_key")
        )

    def try_use_unknown_key_on_office_safe(self):
        """
        使用未知鑰匙打開館長室保險箱，取得倉庫鑰匙。
        """
        if not self.story.has_director_flag("unknown_key_obtained"):
            self.set_system_message("保險箱緊緊鎖著，現在還沒有線索能打開它。")
            return

        if self.is_collectible_collected("storage_key"):
            self.set_system_message("保險箱已經打開過了。")
            return

        if self.active_item_id != "unknown_key":
            self.set_system_message("也許可以試試館長剛才交給你的那把鑰匙。")
            return

        self.active_item_id = None
        self.story.set_director_flag("office_safe_opened")
        self.story.set_director_flag("storage_key_obtained")

        item = self.get_collectible_item("storage_key")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.play_open_door_sound()

        self.start_message_reading([
            "未知的鑰匙插進保險箱後，鎖芯發出低沉的聲響。",
            "保險箱門緩慢打開，裡面放著一把標籤褪色的鑰匙。",
            "你獲得了【倉庫鑰匙】。",
            "也許現在可以去看看倉庫了。"
        ])

    # =========================================================
    # 變異空間與理智值系統
    # =========================================================
    def update_mutation_system(self, dt):
        """
        只有玩家正在觀察某個變異房間時，
        理智值才會持續下降。
        """
        if self.mode != "observation":
            return

        if not self.mutation.is_scene_mutated(self.observation_scene_id):
            return

        self.mutation.update(dt)

        if self.mutation.has_sanity_depleted():
            self.handle_sanity_depleted()


    def handle_sanity_depleted(self):
        """
        理智值歸零：玩家迷失，遊戲從頭開始。
        目前先直接重置遊戲。
        之後若要做 Game Over 畫面，可以再插在這裡。
        """
        self.reset_game()


    def start_mutated_room(self, scene_id, sanity_decay_per_second=None):
        self.mutation.start_mutation(
            scene_id,
            sanity_decay_per_second
        )

        self.switch_to_mutation_bgm()

    def clear_mutated_room(self, scene_id):
        self.mutation.clear_mutation(scene_id)

        if not self.mutation.is_mutation_active():
            self.switch_to_normal_bgm()
        
    
    # =========================================================
    # 走廊區域移動
    # =========================================================
    def try_move_in_hallway(self):
        portal = self.hallway.get_near_portal()

        if portal is None:
            self.set_system_message("附近沒有可以前往的地方。")
            return

        if portal.target_mode == "observation":
            self.try_enter_observation_room(
                scene_id=portal.target_area,
                location_name=portal.name,
                return_mode="hallway",
                return_area_id=self.hallway.current_area_id,
                return_spawn_x=portal.x
            )
            return

        self.stop_walk_sound()
        self.play_open_door_sound()

        self.hallway.move_to_area(
            portal.target_area,
            portal.spawn_x
        )

        self.set_system_message(
            f"你來到了「{self.hallway.current_area.name}」。"
        )

    # =========================================================
    # 觀察狀態
    # =========================================================
    def start_observation(
        self,
        scene_id,
        location_name,
        return_mode="hallway",
        return_area_id=None,
        return_spawn_x=None,
        return_scene_id=None,
        return_location_name=None
    ):
        self.mode = "observation"

        self.observation_scene_id = scene_id
        self.observation_location_name = location_name

        self.observation_return_mode = return_mode

        self.observation_return_area_id = return_area_id
        self.observation_return_spawn_x = return_spawn_x

        self.observation_return_scene_id = return_scene_id
        self.observation_return_location_name = return_location_name

        self.set_system_message(f"你進入了「{location_name}」。")
        if (
            scene_id == "storage_room"
            and not self.story.has_director_flag("storage_light_on")
        ):
            if not self.story.has_director_flag("storage_darkness_seen"):
                self.story.set_director_flag("storage_darkness_seen")
                self.story.set_director_flag("storage_room_entered_first_time")

                self.start_message_reading([
                    "你推開倉庫的門。",
                    "裡面一片漆黑，幾乎伸手不見五指。",
                    "這樣下去，根本看不清裡面有什麼。",
                    "也許得先找到能照亮倉庫的方法。"
                ])
            else:
                self.set_system_message("倉庫裡仍然一片漆黑。")
        if scene_id == "fix_room":
            if not self.story.has_director_flag("fix_room_layout_noticed"):
                self.story.set_director_flag("fix_room_layout_noticed")
                self.start_message_reading([
                    "你進入修復室。",
                    "中間的桌面上擺著一幅修復中的畫。",
                    "右邊的櫃子上，則放著調製顏料用的原料與瓶罐。"
                ])
                return
            
    def return_from_observation(self):
        if self.mutation.is_player_trapped_in(self.observation_scene_id):
            self.set_system_message(
                "空間似乎扭曲了，現在還無法離開。"
            )
            return
        
        self.play_open_door_sound()

        if self.observation_return_mode == "observation":
            return_scene_id = self.observation_return_scene_id
            return_location_name = self.observation_return_location_name

            self.mode = "observation"
            self.observation_scene_id = return_scene_id
            self.observation_location_name = return_location_name

            self.observation_return_mode = "hallway"
            self.observation_return_area_id = "second_floor"

            fix_portal = self.hallway.find_portal("second_floor", "修復室")
            self.observation_return_spawn_x = fix_portal.x if fix_portal else None

            self.observation_return_scene_id = None
            self.observation_return_location_name = ""

            self.set_system_message(f"你回到了「{return_location_name}」。")
            return

        self.mode = "hallway"

        self.hallway.move_to_area(
            self.observation_return_area_id,
            self.observation_return_spawn_x
        )

        self.set_system_message("你回到了原本的走道。")

        self.observation_scene_id = None
        self.observation_location_name = ""

        self.observation_return_mode = "hallway"
        self.observation_return_area_id = "hall_main"
        self.observation_return_spawn_x = None

        self.observation_return_scene_id = None
        self.observation_return_location_name = ""


    def apply_brightness_overlay(self):
        """
        以黑色半透明遮罩模擬畫面亮度調整。
        screen_brightness:
        1.0 = 不壓暗
        0.0 = 最暗
        """
        darkness_alpha = int((1.0 - self.screen_brightness) * 180)

        if darkness_alpha <= 0:
            return

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, darkness_alpha))
        self.screen.blit(overlay, (0, 0))


    def get_dialogue_choice_rects(self):
        node = self.dialogue.get_current_node()

        if node is None:
            return []

        choices = node.get("choices", [])

        if not choices:
            return []

        choice_width = WIDTH - 220
        choice_height = 44
        choice_gap = 10

        box_height = 270
        box_y = HEIGHT - box_height

        start_x = WIDTH // 2 - choice_width // 2
        start_y = box_y + 145

        rects = []

        for i, choice in enumerate(choices):
            rect = pygame.Rect(
                start_x,
                start_y + i * (choice_height + choice_gap),
                choice_width,
                choice_height
            )

            rects.append((i, choice, rect))

        return rects
    def get_puzzle_choice_rects(self):
        puzzle = self.puzzle.get_current_puzzle()

        if puzzle is None:
            return []

        choices = puzzle.get("choices", [])

        if not choices:
            return []

        choice_width = 440
        choice_height = 38
        choice_gap = 10

        start_x = WIDTH // 2 - choice_width // 2
        start_y = 310

        rects = []

        for i, choice in enumerate(choices):
            rect = pygame.Rect(
                start_x,
                start_y + i * (choice_height + choice_gap),
                choice_width,
                choice_height
            )

            rects.append((i, choice, rect))

        return rects
    def handle_puzzle_choice_click(self, mouse_pos):
        if not self.puzzle.is_active():
            return False

        current_puzzle = self.puzzle.get_current_puzzle()

        for index, choice, rect in self.get_puzzle_choice_rects():
            if rect.collidepoint(mouse_pos):
                result = self.puzzle.submit_choice(index)

                if result == "correct":
                    if current_puzzle:
                        self.set_system_message(
                            current_puzzle.get("clear_message", "答對了。")
                        )

                    action = self.puzzle.consume_pending_clear_action()
                    self.handle_puzzle_clear_action(action)
                    return True

                if result == "wrong":
                    if current_puzzle:
                        self.set_system_message(
                            current_puzzle.get("wrong_message", "不對。")
                        )

                    # 答錯：理智值直接減半
                    if self.mutation.is_mutation_active():
                        self.mutation.current_sanity *= 0.5

                        if self.mutation.current_sanity < 1:
                            self.mutation.current_sanity = 0
                            self.mutation.sanity_depleted = True

                    return True

        return False
    def get_fix_room_color_table_rect(self):
        """
        修復室桌子互動區。
        玩家使用色票後，點擊這裡開始調色關卡。
        """
        return pygame.Rect(
            1015,
            155,
            235,
            285
        )
    def get_storage_newspaper_box_rect(self):
        """
        倉庫左下角黑色箱子。
        亮燈後可調查，取得當年剪報。
        """
        return pygame.Rect(
            95,
            425,
            245,
            95
        )


    def get_storage_painting_rects(self):
        """
        倉庫內所有可調查畫作。
        right_white_frame 是真正的高仿太陽之女。
        """
        return [
            {
                "id": "left_shelf_painting",
                "name": "左側架上的畫",
                "rect": pygame.Rect(315, 255, 115, 90),
                "is_target": False
            },
            {
                "id": "middle_floor_painting",
                "name": "中央地上的畫",
                "rect": pygame.Rect(500, 285, 90, 125),
                "is_target": False
            },
            {
                "id": "right_floor_gold_frame",
                "name": "右下角金框畫",
                "rect": pygame.Rect(925, 395, 170, 150),
                "is_target": False
            },
            {
                "id": "right_white_frame",
                "name": "右側櫃子的白色畫框",
                "rect": pygame.Rect(1095, 295, 80, 165),
                "is_target": True
            },
        ]
    def inspect_storage_newspaper_box(self):
        """
        亮燈後調查倉庫左下黑色箱子，取得當年剪報。
        """
        if not self.story.has_director_flag("storage_light_on"):
            self.set_system_message("太暗了，現在什麼也看不清楚。")
            return

        if self.story.has_director_flag("newspaper_clipping_obtained"):
            self.set_system_message("箱子裡已經沒有其他有用的資料了。")
            return

        self.story.set_director_flag("newspaper_clipping_obtained")

        item = self.get_collectible_item("newspaper_clipping")

        if item:
            item["collected"] = True

            if item["name"] not in self.inventory.items:
                self.inventory.items.append(item["name"])

        self.start_message_reading([
            "倉庫左下角放著一只黑色舊箱子。",
            "你翻開箱蓋，裡面塞滿泛黃的報紙與展覽紀錄。",
            "其中一份舊報紙被折得很小，邊緣還有燒焦的痕跡。",
            "你獲得了【舊報紙】。",
            "也許可以打開口袋，仔細讀讀上面的內容。"
        ])

    def inspect_storage_painting(self, painting_data):
        """
        倉庫畫作調查。
        亮燈後所有畫作都可以點擊。
        取得日記前，只能先觀察；取得日記後，右側白色畫框可取得太陽之女。
        """
        if not self.story.has_director_flag("storage_light_on"):
            self.set_system_message("太暗了，現在什麼也看不清楚。")
            return

        self.story.set_director_flag("storage_paintings_checked")
        self.story.set_director_flag("storage_painting_pile_seen")

        # 還沒取得日記前，只能先調查，不能拿高仿畫
        if not self.story.has_girl_flag("diary_obtained"):
            if painting_data["is_target"]:
                self.set_system_message("這幅白色畫框裡的畫似乎比較新，但你還不知道它是不是你要找的那幅。")
            else:
                self.set_system_message("這幅畫看起來只是被收進倉庫的舊展品。")

            return

        # 已經取得日記後，點到真正的目標畫
        if painting_data["is_target"]:
            if self.story.has_girl_flag("high_quality_fake_sunflower_obtained"):
                self.set_system_message("你已經拿走那幅高仿畫了。")
                return

            self.story.set_girl_flag("high_quality_fake_sunflower_obtained")

            self.replace_sunflower_painting_item("high_quality_fake_sunflower")
            self.start_message_reading([
                "你對照日記裡的描述，重新檢查右側櫃子上的白色畫框。",
                "畫中的女孩像被細碎的光包圍，輪廓比肖像廳那幅更加柔和。",
                "雖然光澤仍有些不自然，但它比肖像廳裡那幅更接近日記中的描述。",
                "你獲得了【太陽之女】。"
            ])
            return

        self.set_system_message("這幅畫和日記中的描述對不上。")
    
    def clear_girl_riddle_3_event(self):
        """
        謎語 3 解開後：
        - 解除變異特展廳
        - 小女孩交給玩家肖像館鑰匙
        - 肖像廳仍需玩家自行前往開鎖
        """
        self.story.set_girl_flag("girl_riddle_3_cleared")
        self.story.set_girl_flag("portrait_key_obtained")

        self.clear_mutated_room("special_hall")

        item = self.get_collectible_item("portrait_key")

        if item is None:
            self.set_system_message("錯誤：找不到肖像館鑰匙資料。")
            return

        item["collected"] = True

        if item["name"] not in self.inventory.items:
            self.inventory.items.append(item["name"])

        self.active_item_id = None

        self.start_message_reading([
            "特展廳的空氣逐漸恢復平靜。",
            "小女孩從展櫃後方取出一把藏起來的鑰匙。",
            "「這是肖像館的鑰匙。」",
            "「如果你真的想幫我，就去那裡找《太陽之女》。」",
            "你獲得了【肖像館鑰匙】。"
        ])
    def handle_dialogue_choice_click(self, mouse_pos):
        for index, choice, rect in self.get_dialogue_choice_rects():
            if rect.collidepoint(mouse_pos):
                self.choose_dialogue_option(index)
                return True

        return False
    
    def replace_sunflower_painting_item(self, new_item_id):
        """
        三幅《太陽之女》只在口袋中保留最新取得的一幅。
        舊畫保持 collected=True，避免重新出現在場景；
        但 owned=False，避免口袋反查時抓到舊版本。
        """
        sunflower_item_ids = [
            "fake_sunflower_painting",
            "high_quality_fake_sunflower",
            "true_sunflower_painting"
        ]

        self.inventory.items = [
            item_name
            for item_name in self.inventory.items
            if item_name != "太陽之女"
        ]

        for item_id in sunflower_item_ids:
            item = self.get_collectible_item(item_id)

            if item:
                item["owned"] = False

        new_item = self.get_collectible_item(new_item_id)

        if new_item:
            new_item["collected"] = True
            new_item["owned"] = True

            if new_item["name"] not in self.inventory.items:
                self.inventory.items.append(new_item["name"])
    def start_ending_event(self):
        """
        DEBUG 版結局：
        出口出現後，點擊男廁任意位置，先用文字收束並回到主選單。
        """
        self.pending_return_to_menu_after_messages = True
        self.true_exit_found = False
        self.active_item_id = None

        self.start_message_reading([
            "你走向那扇被遮色片顯現出的出口。",
            "門後沒有聲音，只有一片慢慢擴散的黑。",
            "你回頭看了一眼，十文字美術館的燈光正在一盞盞熄滅。",
            "畫面逐漸暗了下來。",
            "DEBUG：結局暫時返回主選單。"
        ])