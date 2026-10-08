import pygame
import random
from game.beat import Note, LANES, LANE_KEYS, LANE_LABELS, LANE_COLORS


WIDTH, HEIGHT = 480, 640
FPS = 60
BPM = 120
BEAT_DURATION = 60 / BPM
HIT_Y = HEIGHT - 80
HIT_WINDOW = 30
BG = (15, 10, 25)
LANE_W = WIDTH // LANES


class GameEngine:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.hit_sound = pygame.mixer.Sound("assets/hit.wav")

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Rhythm Tap")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 26, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 44, bold=True)
        self.reset()

    def reset(self):
        self.notes = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.misses = 0
        self.spawn_elapsed = 0.0
        self.last_update_time = pygame.time.get_ticks()
        self.speed = 5
        self.frame = 0
        self.feedback = []  # (text, color, ttl, x, y)
        self.game_over = False

        # Task 2: currently active hold note
        self.active_hold = None

    def spawn_note(self):
        lane = random.randint(0, LANES - 1)

        # 25% chance of spawning a hold note
        is_hold = random.random() < 0.25

        self.notes.append(
            Note(
                lane,
                y=-30,
                speed=self.speed,
                is_hold=is_hold
            )
        )

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            # Key pressed
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()

                elif not self.game_over:
                    for i, key in enumerate(LANE_KEYS):
                        if event.key == key:
                            self.process_tap(i)

        return True

    def process_tap(self, lane):
        # Find closest note in this lane near hit zone
        best = None
        best_dist = 9999

        for note in self.notes:
            if note.lane == lane and not note.hit and not note.missed:

                if note is self.active_hold or note.holding:
                    continue

                dist = abs(
                    note.get_hit_position() - HIT_Y
                )

                if dist < best_dist:
                    best_dist = dist
                    best = note

        lane_x = lane * LANE_W + LANE_W // 2

        # No note close enough
        if best is None or best_dist > HIT_WINDOW:
            self.combo = 0

            self.feedback.append(
                [
                    "MISS",
                    (220, 60, 60),
                    40,
                    lane_x,
                    HIT_Y - 30
                ]
            )

            return

        # -----------------------------------------
        # HOLD NOTE
        # -----------------------------------------

        if best.is_hold:

            # Start the hold
            if self.active_hold is None:

                best.holding = True
                best.hold_start_time = pygame.time.get_ticks()

                # Put the head of the hold note
                # exactly on the hit line
                best.y = HIT_Y - Note.HEIGHT // 2

                self.active_hold = best

                self.feedback.append(
                    [
                        "HOLD",
                        (255, 220, 0),
                        40,
                        lane_x,
                        HIT_Y - 30
                    ]
                )

            return

        # -----------------------------------------
        # NORMAL NOTE
        # -----------------------------------------

        best.hit = True

        if best_dist < 8:
            grade, pts = "PERFECT", 300
            col = (255, 220, 0)

        elif best_dist < 18:
            grade, pts = "GREAT", 200
            col = (100, 220, 100)

        else:
            grade, pts = "OK", 100
            col = (180, 180, 255)

        # Task 1 sound
        self.hit_sound.play()

        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.score += pts * max(1, self.combo // 5)

        self.feedback.append(
            [
                grade,
                col,
                40,
                lane_x,
                HIT_Y - 30
            ]
        )

    def release_hold(self, note):
        if note is None:
            return

        if not note.holding:
            return

        current_time = pygame.time.get_ticks()

        held_time = (
            current_time
            - note.hold_start_time
        )

        lane_x = (
            note.lane * LANE_W
            + LANE_W // 2
        )

        # -----------------------------------------
        # Successfully held for 1 second
        # -----------------------------------------

        if held_time >= Note.HOLD_DURATION:

            note.holding = False
            note.hit = True
            note.hold_completed = True

            self.combo += 1
            self.max_combo = max(
                self.max_combo,
                self.combo
            )

            self.score += 300

            self.hit_sound.play()

            self.feedback.append(
                [
                    "PERFECT",
                    (255, 220, 0),
                    40,
                    lane_x,
                    HIT_Y - 30
                ]
            )

        # -----------------------------------------
        # Released too early
        # -----------------------------------------

        else:

            note.holding = False
            note.missed = True
            note.y = HEIGHT + 11

            self.combo = 0
            self.misses += 1

            self.feedback.append(
                [
                    "MISS",
                    (220, 60, 60),
                    40,
                    lane_x,
                    HIT_Y - 30
                ]
            )

        self.active_hold = None

    def update(self):
        if self.game_over:
            return

        self.frame += 1

        current_time = pygame.time.get_ticks()
        elapsed_seconds = (current_time - self.last_update_time) / 1000
        self.last_update_time = current_time
        self.spawn_elapsed += elapsed_seconds

        # -----------------------------------------
        # Spawn notes
        # -----------------------------------------

        while self.spawn_elapsed >= BEAT_DURATION:
            self.spawn_note()
            self.spawn_elapsed -= BEAT_DURATION

            if self.frame % 600 == 0:
                self.speed = min(
                    10,
                    self.speed + 0.5
                )

        # -----------------------------------------
        # Active hold note
        # -----------------------------------------

        if self.active_hold is not None:

            note = self.active_hold

            current_time = pygame.time.get_ticks()

            held_time = (
                current_time
                - note.hold_start_time
            )

            keys = pygame.key.get_pressed()

            # Player released the key
            if not keys[LANE_KEYS[note.lane]]:
                self.release_hold(note)

            # Player successfully held for 1 second
            elif held_time >= Note.HOLD_DURATION:
                self.release_hold(note)

        # -----------------------------------------
        # Update notes
        # -----------------------------------------

        for note in self.notes:

            if note.hit or note.missed:
                continue

            # IMPORTANT:
            # Don't move or miss a note while
            # the player is actively holding it.
            if note.holding:
                continue

            note.update()

            if (
                not note.hit
                and not note.missed
                and note.y > HIT_Y + HIT_WINDOW + Note.HEIGHT
            ):
                note.missed = True
                self.misses += 1
                self.combo = 0

                lane_x = (
                    note.lane * LANE_W
                    + LANE_W // 2
                )

                self.feedback.append(
                    [
                        "MISS",
                        (220, 60, 60),
                        40,
                        lane_x,
                        HIT_Y - 30
                    ]
                )

        # -----------------------------------------
        # Remove finished notes
        # -----------------------------------------

        self.notes = [
            n for n in self.notes
            if not (
                n.hit
                or (
                    n.missed
                    and n.y > HEIGHT + 10
                )
            )
        ]

        # -----------------------------------------
        # Feedback
        # -----------------------------------------

        self.feedback = [
            [t, c, ttl - 1, x, y]
            for t, c, ttl, x, y in self.feedback
            if ttl > 1
        ]

        # -----------------------------------------
        # Game over
        # -----------------------------------------

        if self.misses >= 15:
            self.game_over = True

    def draw(self):
        self.screen.fill(BG)

        # Lane dividers
        for i in range(LANES + 1):
            pygame.draw.line(
                self.screen,
                (40, 40, 60),
                (i * LANE_W, 0),
                (i * LANE_W, HEIGHT),
                1
            )

        # Hit line
        pygame.draw.line(
            self.screen,
            (80, 80, 100),
            (0, HIT_Y),
            (WIDTH, HIT_Y),
            2
        )

        for i in range(LANES):
            lx = i * LANE_W + LANE_W // 2

            pygame.draw.rect(
                self.screen,
                LANE_COLORS[i],
                pygame.Rect(
                    lx - Note.WIDTH // 2,
                    HIT_Y - 12,
                    Note.WIDTH,
                    24
                ),
                border_radius=6
            )

            lbl = self.font.render(
                LANE_LABELS[i],
                True,
                (20, 20, 20)
            )

            self.screen.blit(
                lbl,
                (lx - lbl.get_width() // 2, HIT_Y - 10)
            )

        # Notes
        for note in self.notes:
            if note.hit:
                continue

            lx = note.lane * LANE_W + LANE_W // 2

            # Normal note
            if not note.is_hold:

                rect = note.get_rect(lx)

                pygame.draw.rect(
                    self.screen,
                    LANE_COLORS[note.lane],
                    rect,
                    border_radius=5
                )

            # Hold note
            else:

                # Long body
                body_rect = pygame.Rect(
                    lx - Note.WIDTH // 2,
                    int(note.y),
                    Note.WIDTH,
                    Note.HOLD_HEIGHT
                )

                pygame.draw.rect(
                    self.screen,
                    LANE_COLORS[note.lane],
                    body_rect,
                    border_radius=5
                )

                # Head
                head_rect = pygame.Rect(
                    lx - Note.WIDTH // 2,
                    int(note.y),
                    Note.WIDTH,
                    Note.HEIGHT
                )

                pygame.draw.rect(
                    self.screen,
                    LANE_COLORS[note.lane],
                    head_rect,
                    border_radius=5
                )

        # Feedback
        for text, color, ttl, x, y in self.feedback:
            surf = self.font.render(text, True, color)
            alpha = min(255, ttl * 7)
            surf.set_alpha(alpha)

            self.screen.blit(
                surf,
                (x - surf.get_width() // 2, y)
            )

        # HUD
        sc = self.font.render(
            f"Score: {self.score}",
            True,
            (220, 220, 220)
        )

        co = self.font.render(
            f"Combo: {self.combo}x",
            True,
            (255, 220, 80)
        )

        mi = self.font.render(
            f"Misses: {self.misses}/15",
            True,
            (220, 100, 100)
        )

        self.screen.blit(sc, (10, 10))
        self.screen.blit(co, (10, 40))
        self.screen.blit(mi, (WIDTH - 170, 10))

        if self.game_over:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            self.screen.blit(ov, (0, 0))

            msg = self.big_font.render(
                "GAME OVER",
                True,
                (220, 60, 60)
            )

            sc_msg = self.font.render(
                f"Final Score: {self.score}  Max Combo: {self.max_combo}x",
                True,
                (200, 200, 200)
            )

            restart = self.font.render(
                "Press R to Restart",
                True,
                (160, 160, 160)
            )

            self.screen.blit(
                msg,
                (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 70)
            )

            self.screen.blit(
                sc_msg,
                (WIDTH // 2 - sc_msg.get_width() // 2, HEIGHT // 2)
            )

            self.screen.blit(
                restart,
                (WIDTH // 2 - restart.get_width() // 2, HEIGHT // 2 + 50)
            )

        pygame.display.flip()

    def run(self):
        running = True

        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()