import pygame

from .audio import Audio
from .combat import Duel
from .config import Element, FPS, HEIGHT, TITLE, WIDTH
from .effects import Effects
from .rendering import Renderer
from .progression import ProgressStore
from .question_database import QuestionDatabase
from .curriculum import StudySelection
from .viewport import Viewport


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption(TITLE)
        self.canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.viewport = Viewport(WIDTH, HEIGHT, *self.screen.get_size())
        self.scaled_canvas = None
        self.clock = pygame.time.Clock()
        self.renderer = Renderer()
        self.audio = Audio()
        self.running = True
        self.elapsed = 0.0
        self.show_guide = False
        self.difficulty = "Duelist"
        self.database = QuestionDatabase()
        self.database.initialise()
        self.selection = StudySelection()
        self.menu_field = "subtopic"
        self.revision_summary = self.database.revision_summary_for(self.selection)
        self.progress_store = ProgressStore()
        self.progress = self.progress_store.load()
        self.save_error = False
        self.phase = "menu"
        self.countdown = 0.0
        self._new_match()

    def _new_match(self):
        self.duel = Duel(difficulty=self.difficulty, rank_index=self.progress.rank_index,
                         database=self.database, selection=self.selection)
        self.effects = Effects(self.audio)
        self.answer = ""
        self.match_recorded = False
        self.last_rank_change = None
        self.show_guide = False

    def _start_match(self):
        self._new_match()
        self.countdown = 3.75
        self.phase = "countdown"

    def _cycle_difficulty(self):
        order = ("Apprentice", "Duelist", "Archmage")
        self.difficulty = order[(order.index(self.difficulty) + 1) % len(order)]

    def _cycle_field(self, field: str, offset: int):
        selection = self.selection
        if field == "course":
            choices = self.database.courses()
            current = selection.course
        elif field == "board":
            choices = self.database.boards(selection.course)
            current = selection.board
        elif field == "subject":
            choices = self.database.subjects(selection.course, selection.board)
            current = selection.subject
        else:
            choices = self.database.subtopics(selection.course, selection.board, selection.subject)
            current = selection.subtopic
        if not choices:
            return
        index = choices.index(current) if current in choices else 0
        choice = choices[(index + offset) % len(choices)]
        course = choice if field == "course" else selection.course
        boards = self.database.boards(course)
        board = choice if field == "board" else selection.board if selection.board in boards else boards[0]
        subjects = self.database.subjects(course, board)
        subject = choice if field == "subject" else selection.subject if selection.subject in subjects else subjects[0]
        subtopics = self.database.subtopics(course, board, subject)
        subtopic = choice if field == "subtopic" else selection.subtopic if selection.subtopic in subtopics else subtopics[0]
        self.selection = StudySelection(course, board, subject, subtopic)
        self.revision_summary = self.database.revision_summary_for(self.selection)

    def _cycle_menu_row(self, offset: int):
        fields = ("course", "board", "subject", "subtopic")
        self.menu_field = fields[(fields.index(self.menu_field) + offset) % len(fields)]

    def _submit_choice(self, choice: int):
        if self.phase != "playing" or self.show_guide or not self.duel.player_question.options:
            return
        self.duel.submit_answer(str(choice))

    def _record_match(self):
        if not self.duel.finished or self.match_recorded:
            return
        self.match_recorded = True
        self.revision_summary = self.database.revision_summary_for(self.selection)
        self.last_rank_change = self.progress.record(self.duel.winner)
        try:
            self.progress_store.save(self.progress)
            self.save_error = False
        except OSError:
            self.save_error = True
        self.phase = "results"

    def _submit(self):
        if self.phase != "playing":
            return
        if self.duel.player_question.options:
            return
        result = self.duel.submit_answer(self.answer)
        if result is not None:
            self.answer = ""

    def _key_down(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.phase == "menu":
                self.running = False
            else:
                self.phase = "menu"
                self.revision_summary = self.database.revision_summary_for(self.selection)
                self.show_guide = False
            return
        if self.phase == "menu":
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._start_match()
            elif event.key == pygame.K_TAB:
                self._cycle_difficulty()
            elif event.key == pygame.K_UP:
                self._cycle_menu_row(-1)
            elif event.key == pygame.K_DOWN:
                self._cycle_menu_row(1)
            elif event.key == pygame.K_LEFT:
                self._cycle_field(self.menu_field, -1)
            elif event.key == pygame.K_RIGHT:
                self._cycle_field(self.menu_field, 1)
            return
        if self.phase == "countdown":
            return
        if self.phase == "results":
            if event.key == pygame.K_r or event.key == pygame.K_RETURN:
                self._start_match()
            elif event.key == pygame.K_m:
                self.phase = "menu"
                self.revision_summary = self.database.revision_summary_for(self.selection)
            return
        if event.key == pygame.K_h:
            self.show_guide = not self.show_guide
            return
        if self.show_guide:
            return
        spell_keys = {
            pygame.K_q: Element.FIRE,
            pygame.K_w: Element.EARTH,
            pygame.K_e: Element.WATER,
            pygame.K_r: Element.AIR,
            pygame.K_t: Element.SPIRIT,
        }
        if event.key == pygame.K_SPACE:
            self.duel.activate_pulse("player")
        elif event.key in spell_keys:
            self.duel.select_element(spell_keys[event.key])
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._submit()
        elif event.key == pygame.K_BACKSPACE:
            self.answer = self.answer[:-1]
        elif event.unicode.isascii() and event.unicode.isdigit():
            if self.duel.player_question.options:
                if event.unicode in "1234":
                    self._submit_choice(int(event.unicode))
            elif self.duel.player_question_active and len(self.answer) < 4:
                self.answer += event.unicode

    def _mouse_down(self, event):
        if event.button != 1:
            return
        point = self.viewport.to_virtual(event.pos)
        if point is None:
            return
        if self.phase == "menu":
            if self.renderer.menu_play_rect.collidepoint(point):
                self._start_match()
            elif self.renderer.menu_difficulty_rect.collidepoint(point):
                self._cycle_difficulty()
            else:
                for field, (previous, value, following) in self.renderer.menu_selector_rects.items():
                    if previous.collidepoint(point):
                        self.menu_field = field
                        self._cycle_field(field, -1)
                        break
                    if following.collidepoint(point):
                        self.menu_field = field
                        self._cycle_field(field, 1)
                        break
                    if value.collidepoint(point):
                        self.menu_field = field
                        break
            return
        if self.phase == "results":
            if self.renderer.rematch_rect.collidepoint(point):
                self._start_match()
            elif self.renderer.back_menu_rect.collidepoint(point):
                self.phase = "menu"
                self.revision_summary = self.database.revision_summary_for(self.selection)
            return
        if self.phase != "playing" or self.show_guide:
            return
        for element, rect in self.renderer.spell_rects.items():
            if rect.collidepoint(point):
                self.duel.select_element(element)
                return
        if self.duel.player_question.options:
            for index, rect in enumerate(self.renderer.choice_rects, start=1):
                if rect.collidepoint(point):
                    self._submit_choice(index)
                    return
        elif self.renderer.cast_rect.collidepoint(point):
            self._submit()

    def _resize(self, size):
        width, height = max(640, size[0]), max(400, size[1])
        if self.screen.get_size() != (width, height):
            self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.viewport = Viewport(WIDTH, HEIGHT, width, height)
        self.scaled_canvas = None

    def _display(self):
        current_size = self.screen.get_size()
        if current_size != (self.viewport.window_width, self.viewport.window_height):
            self._resize(current_size)
        self.screen.fill((26, 19, 42))
        size = self.viewport.size
        origin = self.viewport.origin
        if size == (WIDTH, HEIGHT):
            self.screen.blit(self.canvas, origin)
        else:
            if self.scaled_canvas is None or self.scaled_canvas.get_size() != size:
                self.scaled_canvas = pygame.Surface(size).convert()
            pygame.transform.smoothscale(self.canvas, size, self.scaled_canvas)
            self.screen.blit(self.scaled_canvas, origin)
        pygame.display.flip()

    def run(self):
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 1000.0
                self.elapsed += dt
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.VIDEORESIZE:
                        self._resize(event.size)
                    elif event.type == pygame.KEYDOWN:
                        self._key_down(event)
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        self._mouse_down(event)
                if self.phase == "countdown":
                    self.countdown -= dt
                    if self.countdown <= 0:
                        self.phase = "playing"
                        self.countdown = 0.0
                elif self.phase == "playing" and not self.show_guide:
                    previous_question = self.duel.player_question
                    self.duel.update(dt)
                    if self.duel.player_question is not previous_question:
                        self.answer = ""
                    self._record_match()
                    self.effects.on_events(self.duel.pop_events())
                    self.effects.trail(self.duel.projectiles, dt)
                    self.effects.update(dt)
                mouse_pos = self.viewport.to_virtual(pygame.mouse.get_pos()) or (-1, -1)
                if self.phase == "menu":
                    self.renderer.draw_menu(self.canvas, self.progress, self.difficulty,
                                            self.selection.subtopic, self.elapsed, mouse_pos, self.save_error,
                                            self.revision_summary, self.selection, self.menu_field)
                else:
                    self.renderer.draw(self.canvas, self.duel, self.answer, self.effects,
                                       self.elapsed, mouse_pos, self.show_guide,
                                       self.progress, self.last_rank_change, self.save_error)
                    if self.phase == "countdown":
                        self.renderer.draw_countdown(self.canvas, self.countdown)
                self._display()
        finally:
            pygame.quit()
