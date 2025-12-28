import pygame
import asyncio
import pygbag
import os 
import random

def get_path(relative_path):
    return os.path.join(os.path.dirname(__file__), relative_path)

player1 = None
player2 = None
current_bg_img = None
cpu_enemies = []  # Lista na przeciwników w trybie Single
current_map_index = 0 # Indeks aktualnego pokoju w Single Player

pygame.init()
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 500
screen = pygame.display.set_mode((1000, 500))
clock = pygame.time.Clock()

pygame.font.init()
# Używamy None dla bezpieczeństwa w przeglądarce
font_main = pygame.font.Font(None, 70)
font_sub = pygame.font.Font(None, 40)

# Stany gry
STATE_MAP_SELECT = "map_select"
selected_map_index = 0
STATE_MENU = "menu"
STATE_CHAR_SELECT = "char_select"
STATE_PLAYING = "playing"
game_state = STATE_MENU
STATE_SETTINGS = "settings"
setting_selected_idx = 0  # Który klawisz z listy zmieniamy
is_binding = False        # Czy czekamy na wciśnięcie klawisza
# Wybory i nawigacja menu
menu_options = ["Jeden Gracz", "Dwóch Graczy", "USTAWIENIA"]
menu_index = 0
game_mode = "multi"
available_chars = ["Soldier", "Orc", "Knight", "Golem"]
p1_char_index = 0
p2_char_index = 1
# Sterowanie
P1_CONTROLS = {'left': pygame.K_a, 'right': pygame.K_d, 'jump': pygame.K_w, 'atk1': pygame.K_r, 'atk2': pygame.K_t, 'special': pygame.K_y, 'block': pygame.K_u}
P2_CONTROLS = {'left': pygame.K_LEFT, 'right': pygame.K_RIGHT, 'jump': pygame.K_UP, 'atk1': pygame.K_m, 'atk2': pygame.K_COMMA, 'special': pygame.K_PERIOD, 'block': pygame.K_l}

# --- FUNKCJA RYSUJĄCA PRZYCISK KLAWIATUROWY ---
def draw_keyboard_button(text, x, y, width, height, is_selected):
    rect = pygame.Rect(x, y, width, height)
    # Jeśli wybrany - świeci, jeśli nie - jest ciemny
    color = (100, 100, 255) if is_selected else (50, 50, 50)
    pygame.draw.rect(screen, color, rect, border_radius=10)
    if is_selected:
        pygame.draw.rect(screen, (255, 255, 255), rect, 3, border_radius=10)

    text_surf = font_sub.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)


# --- KONFIGURACJA TILESETU ---
# Plik: tileset.png (wymiary 96x160)
# Kafelki: 16x16
# 96 / 16 = 6 kafelków w rzędzie
TILE_SCALE = 3
TILE_SIZE_ORIGINAL = 16
TILE_SIZE = TILE_SIZE_ORIGINAL * TILE_SCALE

def load_tiles_from_folder(folder_path, scale):
    tiles_list = []
    # Zakładamy, że kafelki są ponumerowane od 0 do np. 59
    # tak jak w Twoim tilesecie 96x160 (6x10 = 60 kafelków)
    for i in range(60): 
        file_path = f"{folder_path}/kafelek{i}.png"
        try:
            # Wczytujemy pojedynczy plik 16x16
            tile = pygame.image.load(file_path).convert_alpha()
            # Skalujemy go od razu do 48x48
            tile = pygame.transform.scale(tile, (16 * scale, 16 * scale))
            tiles_list.append(tile)
        except:
            # Jeśli brakuje jakiegoś numeru, wstawiamy pusty różowy kwadrat (ułatwia debugowanie)
            err_surf = pygame.Surface((16 * scale, 16 * scale))
            err_surf.fill((255, 0, 255)) 
            tiles_list.append(err_surf)
            # print(f"Brak kafelka: {file_path}") # Opcjonalne do logów
            
    return tiles_list

# Wywołanie (upewnij się, że ścieżka jest poprawna)
tiles = load_tiles_from_folder("Assets/kafelki", TILE_SCALE)

# --- NOWA MAPA ---
# 0 - puste tło
# 1, 2 - kafelki podłogi (na przemian)
# COLLISION_TILES zawiera 1 i 2, żeby można było po nich chodzić
COLLISION_TILES = [0, 1, 2, 13, 15, 34, 35, 36]

# Twoja obecna mapa
map_forest = [
    ['B']*23,
    ['B']*23,
    [13, 2, 15] + ['B']*17 + [13, 2, 15], 
    ['B']*23,
    ['B']*7 + [34, 35, 35, 35, 35, 36] + ['B']*10,
    ['B']*23,
    ['B']*23,
    ['B']*23,
    ['B']*23,
    [2]*23, # Podłoga na całą szerokość + zapas
]

# Nowa mapa: Arena (dwie wysokie platformy, pusto w środku)
map_arena = [
    ['B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B'],
    ['B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B'],
    [13, 2, 15, 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 13, 2, 15], # Boczne platformy
    ['B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B'],
    ['B', 'B', 'B', 'B', 'B', 'B', 'B', 34, 35, 35, 35, 35, 36, 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B'], # Środkowa platforma
    ['B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B'],
    ['B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B'],
    ['B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B'],
    ['B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B'],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]

available_maps = [
    {
        "name": "Gesty Las", 
        "data": map_forest, 
        "bg_path": "Assets/Backgrounds/forest.png"
    },
    {
        "name": "Podniebna Arena", 
        "data": map_arena, 
        "bg_path": "Assets/Backgrounds/sky.png"
    }
] 
B = 'B'   
single_levels = [
    {
        "name": "Poziom 1: Przedpole",
        "data": [
            [B]*23, [B]*23,
            [B]*5 + ['O'] + [B]*10 + ['O'] + [B]*6, # Dwóch orków na start
            [B]*23, [B]*23, [B]*23, [B]*23, [B]*23, [B]*23,
            [2]*23,
        ],
        "bg_path": "Assets/Backgrounds/forest.png"
    },
    {
        "name": "Poziom 2: Strażnik",
        "data": [
            [B]*23, [B]*23,
            [13, 2, 15] + [B]*17 + [13, 2, 15],
            [B]*23, [B]*11 + ['G'] + [B]*11, # Golem na środku
            [B]*23, [B]*23, [B]*23, [B]*23,
            [2]*23,
        ],
        "bg_path": "Assets/Backgrounds/sky.png"
    }
]
# Funkcja budująca kolizje (wywołuj przy starcie walki)
platforms = []
def build_platforms(map_data):
    global game_map, platforms, cpu_enemies
    game_map = map_data
    platforms.clear()
    cpu_enemies.clear() # Ważne: czyścimy wrogów przy zmianie mapy

    for row_idx, row in enumerate(map_data):
        for col_idx, tile_idx in enumerate(row):
            pixel_x = col_idx * TILE_SIZE
            pixel_y = row_idx * TILE_SIZE
            
            # 1. Obsługa kafelków (Liczby)
            if isinstance(tile_idx, int):
                if tile_idx in COLLISION_TILES:
                    new_rect = pygame.Rect(pixel_x, pixel_y, TILE_SIZE, TILE_SIZE)
                    platforms.append(new_rect)
            
            # 2. Obsługa przeciwników w trybie Single (Litery)
            elif game_mode == "single":
                if tile_idx == 'O':
                    # Upewnij się, że klasa Orc jest zdefiniowana!
                    cpu_enemies.append(Orc(pixel_x, pixel_y)) 
                elif tile_idx == 'G':
                    cpu_enemies.append(Golem(pixel_x, pixel_y))
                elif tile_idx == 'K':
                    cpu_enemies.append(HumanSoldier(pixel_x, pixel_y))
                          
# --- POPRAWKA W RYSOWANIU (wewnątrz pętli gry) ---
# Zamień fragment rysowania postaci na ten poniżej, żeby stały NA klockach:
# img_rect = player.image.get_rect(centerx=player.rect.centerx, bottom=player.rect.bottom)
# screen.blit(player.image, img_rect)
# --- KLASA POCISKU ---
class Arrow(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner):
        super().__init__()
        self.owner = owner
        self.speed = 12
        self.image = pygame.Surface((20, 4))
        self.image.fill((200, 200, 200))
        self.rect = self.image.get_rect()
        self.active = True  # NOWE: Flaga aktywności
        
        if direction == 'right':
            self.rect.left = x
            self.vel_x = self.speed
        else:
            self.rect.right = x
            self.vel_x = -self.speed
        
        self.rect.centery = y 
        self.damage = 15

    def update(self, targets): # Zmieniamy argumenty na listę celów
        self.rect.x += self.vel_x 
        
        # Sprawdzenie kolizji z każdym potencjalnym celem
        for target in targets:
            if target and target != self.owner and not target.is_dead:
                if self.rect.colliderect(target.hitbox):
                    if not target.is_blocking:
                        target.take_damage(self.damage)
                    self.active = False # Zamiast remove, flagujemy
                    return

        # Usuwanie poza ekranem
        if self.rect.right < 0 or self.rect.left > 1000: # 1000 to SCREEN_WIDTH
            self.active = False
# --- KLASA BAZOWA ---
class Character(pygame.sprite.Sprite):
    # Dodajemy hp, speed i damage do argumentów (z domyślnymi wartościami)
    def __init__(self, x, y, folder, scale=2.5, hp=100, speed=5, damage=10):
        super().__init__()
        self.folder = folder
        self.scale = scale
        
        # STATYSTYKI (teraz poprawnie przypisane z argumentów)
        self.max_hp = hp
        self.current_hp = hp
        self.vel = speed
        self.damage = damage # Używamy 'damage' zgodnie z Twoją funkcją kolizji
        
        # Reszta Twoich zmiennych...
        self.animations = {}
        self.state = 'idle'
        self.frame_index = 0
        self.direction = 'right'
        self.is_attacking = False
        self.is_blocking = False
        self.is_dead = False
        self.hit_cooldown = 0
        self.rect = pygame.Rect(x, y, 40, 60)
        self.hitbox = pygame.Rect(x, y, 40, 60)
        self.vel_y = 0
        self.gravity = 0.8
        self.jump_height = -16
        self.is_jumping = False
        self.image = pygame.Surface((100, 100))
        self.cpu_action_timer = 0
        self.cpu_current_action = None

    def load_sheet(self, filename, frame_count, width, height):
        path = f"{self.folder}/{filename}"
        print(f"Próbuję załadować: {path}") # To pojawi się w konsoli F12
        try:
            sheet = pygame.image.load(path).convert_alpha()
            frames = []
            for i in range(frame_count):
                frame = sheet.subsurface((i * width, 0, width, height))
                frame = pygame.transform.scale(frame, (int(width * self.scale), int(height * self.scale)))
                frames.append(frame)
            return frames
        except Exception as e:
            print(f"Brak pliku: {path}")
            surf = pygame.Surface((50, 50))
            surf.fill((100, 0, 0))
            return [surf] * frame_count

    def update_hitbox(self):
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.centery = self.rect.centery - 5
        
    def take_damage(self, amount):
        if self.is_dead:
            return
            
        # Jeśli postać blokuje, całkowicie ignorujemy obrażenia
        if self.is_blocking:
            # Tutaj można dodać dźwięk parowania (opcjonalnie)
            return 

        self.current_hp -= amount
        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_dead = True
            self.state = 'death'
        else:
            self.state = 'hit'
        
        self.frame_index = 0
    def draw_hp_bar(self, surface, x, y, align_right=False):
        bar_w, bar_h = 300, 25
        hp_w = int(bar_w * (self.current_hp / self.max_hp))
        if align_right:
            pygame.draw.rect(surface, (255, 0, 0), (x - bar_w, y, bar_w, bar_h))
            pygame.draw.rect(surface, (0, 255, 0), (x - hp_w, y, hp_w, bar_h))
            pygame.draw.rect(surface, (255, 255, 255), (x - bar_w, y, bar_w, bar_h), 2)
        else:
            pygame.draw.rect(surface, (255, 0, 0), (x, y, bar_w, bar_h))
            pygame.draw.rect(surface, (0, 255, 0), (x, y, hp_w, bar_h))
            pygame.draw.rect(surface, (255, 255, 255), (x, y, bar_w, bar_h), 2)

    def update_animation(self):
        # 1. Wybór odpowiedniej listy klatek
        if self.is_dead:
            frames = self.animations['death']
            self.frame_index = min(self.frame_index + 0.15, len(frames) - 1)
        elif self.state == 'block' and self.is_blocking:
            frames = self.animations.get('block', self.animations['idle'])
            self.frame_index = min(self.frame_index + 0.15, len(frames) - 1)
        else:
            frames = self.animations.get(self.state, self.animations['idle'])
            anim_speed = 0.25 if (self.is_attacking or self.state == 'hit') else 0.18
            self.frame_index += anim_speed

            if self.frame_index >= len(frames):
                if self.is_attacking or self.state == 'hit':
                    self.is_attacking = False
                    self.state = 'idle'
                self.frame_index = 0 

        # 2. Pobranie obrazu (TYLKO RAZ NA KOŃCU)
        self.image = frames[int(self.frame_index)]
        if self.direction == 'left':
            self.image = pygame.transform.flip(self.image, True, False)

    def apply_gravity(self, platforms_list=None):
        if platforms_list is None:
            platforms_list = platforms
            
        self.vel_y += self.gravity
        self.rect.y += self.vel_y
    
        # Sprawdzanie kolizji z platformami
        for platform in platforms_list:
            if self.rect.colliderect(platform):
                if self.vel_y > 0: # Tylko gdy spadamy
                    # Sprawdzamy, czy przed ruchem byliśmy nad platformą 
                    # (zapobiega to "teleportacji" do boku kafelka)
                    if self.rect.bottom - self.vel_y <= platform.top :
                        self.rect.bottom = platform.top
                        self.vel_y = 0
                        self.is_jumping = False
        if game_mode == "single" and self == player1:
            # Lewa krawędź zawsze blokuje
            if self.rect.left < 0: self.rect.left = 0
            
            # Prawa krawędź blokuje, jeśli żyją wrogowie
            enemies_alive = any(not e.is_dead for e in cpu_enemies)
            if enemies_alive:
                if self.rect.right > SCREEN_WIDTH: self.rect.right = SCREEN_WIDTH
            # Jeśli nie ma wrogów, pozwalamy wyjść poza SCREEN_WIDTH (logika przejścia w main)


    def check_attack_collision(self, target):
        if self.is_attacking and self.state in ['attack1', 'attack2'] and 2 <= int(self.frame_index) <= 5:
            
            attack_rect = pygame.Rect(0, 0, 40, 60)
            
            if self.direction == 'right':
                attack_rect.left = self.hitbox.right
            else:
                attack_rect.right = self.hitbox.left
            
            attack_rect.centery = self.hitbox.centery

            targets_to_check = target if isinstance(target, list) else [target]

            for t in targets_to_check:
                if t and t != self and not t.is_dead:
                    target_box = getattr(t, 'hitbox', t.rect)
                    
                    if attack_rect.colliderect(target_box):
                        if t.hit_cooldown == 0:
                            # --- ZMIANA TUTAJ: Pobieramy siłę ataku postaci ---
                            dmg = getattr(self, 'damage', 10) # Domyślnie 10, jeśli nie ustawiono
                            t.take_damage(dmg)
                            
                            t.hit_cooldown = 20
                            print(f"Trafiono! Obrażenia: {dmg}")

    def screen_wrap(self):
        if self.rect.centerx > SCREEN_WIDTH: self.rect.centerx = 0
        elif self.rect.centerx < 0: self.rect.centerx = SCREEN_WIDTH
    def face_target(self, target):
        if not self.is_dead and not self.is_attacking:
            if self.rect.centerx < target.rect.centerx:
                self.direction = 'right'
            else:
                self.direction = 'left'

    def update_cpu(self, target, arrows_list):
        if self.is_dead:
            self.update_animation()
            return

        import random
        dx = target.rect.centerx - self.rect.centerx
        dy = target.rect.centery - self.rect.centery  # Dodano dy!
        distance = abs(dx)
        
        cpu_keys = {'left': False, 'right': False, 'jump': False, 
                    'atk1': False, 'atk2': False, 'special': False, 'block': False}

        # --- REAKCJA NA STRZAŁY ---
        for arrow in arrows_list:
            if arrow.owner != self and abs(arrow.rect.centerx - self.rect.centerx) < 250:
                if random.random() < 0.5: 
                    cpu_keys['block'] = True
                elif not self.is_jumping:
                    cpu_keys['jump'] = True

        # --- LOGIKA TIMERA ---
        if self.cpu_action_timer > 0:
            if self.cpu_current_action:
                cpu_keys[self.cpu_current_action] = True
            self.cpu_action_timer -= 1
        else:
            self.cpu_current_action = None

            # --- RUCH I SKOKI ---
            if not self.is_attacking:
                # Szansa na podążanie w stronę gracza
                if random.random() < 0.6: # 60% szans na reakcję ruchu w tej klatce
                    if distance > 50:
                        if dx > 0: cpu_keys['right'] = True
                        else: cpu_keys['left'] = True
                    elif distance < 30:
                        if dx > 0: cpu_keys['left'] = True
                        else: cpu_keys['right'] = True

                # --- SKOK (Reakcja na gracza) ---
                if not self.is_jumping:
                    # Skocz, jeśli gracz jest wyżej lub gracz skacze (szansa 5%)
                    if (dy < -30 or target.is_jumping) and random.random() < 0.05:
                        cpu_keys['jump'] = True
                    # Czysto losowy skok (szansa 0.5%)
                    elif random.random() < 0.001:
                        cpu_keys['jump'] = True

            # --- WALKA ---
            if not self.is_attacking and self.state != 'hit':
                # Blokowanie gracza
                if target.is_attacking and distance < 80:
                    if random.random() < 0.7: cpu_keys['block'] = True

                if not cpu_keys['block']:
                    if distance <= 60:
                        chance = random.random()
                        if chance < 0.06: cpu_keys['atk1'] = True
                        elif chance < 0.04: cpu_keys['atk2'] = True
                    elif distance > 250 and random.random() < 0.01:
                        cpu_keys['special'] = True
                        self.cpu_action_timer = 50 # Blokada na czas animacji łuku
                        self.cpu_current_action = 'special'

        self.apply_cpu_controls(cpu_keys, target, arrows_list)
    def apply_cpu_controls(self, keys, target, arrows_list):
        # 1. Resetujemy flagi ataku, jeśli nie ma akcji (opcjonalnie, zależnie od logiki)
        
        # 2. Blokowanie (Tylko na ziemi i gdy nie atakuje)
        self.is_blocking = keys['block'] and not self.is_jumping and not self.is_attacking
        
        if self.is_blocking:
            self.state = 'block'
            # Podczas bloku CPU się nie rusza
        else:
            # 3. Skok
            if keys['jump'] and not self.is_jumping:
                self.vel_y = self.jump_height
                self.is_jumping = True
                self.state = 'jump'
                self.frame_index = 0
    
            # 4. Ruch
            if keys['left']:
                self.rect.x -= self.vel
                self.direction = 'left'
                if not self.is_jumping and not self.is_attacking: self.state = 'walk'
            elif keys['right']:
                self.rect.x += self.vel
                self.direction = 'right'
                if not self.is_jumping and not self.is_attacking: self.state = 'walk'

            # 5. Ataki
            if keys['atk1']: 
                self.state = 'attack1'; self.is_attacking = True; self.frame_index = 0
            elif keys['atk2']: 
                self.state = 'attack2'; self.is_attacking = True; self.frame_index = 0
            elif keys['special']:
                 # Dodaj to sprawdzenie, żeby nie wywalało błędu u Orca
                 if self.folder.endswith("Soldier"):
                    self.state = 'bow'; self.is_attacking = True; self.frame_index = 0; self.arrow_shot = False
        
        # 6. Aktualizacje fizyki
        self.apply_gravity(platforms) # Dodano argument 'platforms'
        self.update_hitbox()
        self.check_attack_collision(target)
        if self.hit_cooldown > 0: self.hit_cooldown -= 1
        self.update_animation()



class HealthPotion(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # Możesz załadować własny obrazek: pygame.image.load("Assets/potion.png")
        self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 0, 0), (12, 12), 10) # Czerwone kółko jako placeholder
        
        self.rect = self.image.get_rect()
        self.rect.x = x  # Używamy x przekazanego w argumencie
        self.rect.y = y  
        self.vel_y = 0
        self.gravity = 0.2  # DODATNIA grawitacja (mikstura spada w dół)
        self.max_speed = 1
        self.heal_amount = 25

    def update(self, platforms_list, players):
        # Spadanie
        self.vel_y += self.gravity
        self.rect.y += self.vel_y

        # Kolizja z podłogą
        for platform in platforms_list:
            if self.rect.colliderect(platform):
                if self.vel_y > 0:
                    self.rect.bottom = platform.top
                    self.vel_y = 0

        # Kolizja z graczami
        for p in players:
            if p and not p.is_dead and self.rect.colliderect(p.hitbox):
                p.current_hp = min(p.max_hp, p.current_hp + self.heal_amount)
                return True # Miksturka do usunięcia
        return False
class Golem(Character):
    def __init__(self, x, y):
        # Ścieżka do folderu z Golemem
        folder_path = "Assets/Golem"
        
        super().__init__(x, y, folder_path, scale=2.8, hp=200, speed=3, damage=20) # Golem może być nieco większy
        self.image_offset_y = 0  # Golem jest duży i wypełnia klatkę
        # Wymiary klatki Golema: 90x64
        W, H = 90, 64
         

        self.animations = {
            'idle':    self.load_sheet('Golem_1_idle.png', 8, W, H),
            'walk':    self.load_sheet('Golem_1_walk.png', 10, W, H),
            'attack1': self.load_sheet('Golem_1_attack.png', 11, W, H),
            'attack2': self.load_sheet('Golem_1_attack.png', 11, W, H), # Używamy tego samego ataku
            'hit':     self.load_sheet('Golem_1_hurt.png', 4, W, H),
            'death':   self.load_sheet('Golem_1_die.png', 11, W, H),
            # Golem nie ma skoku/bloku w Twoim zestawie, używamy IDLE żeby uniknąć błędów
            'jump':    self.load_sheet('Golem_1_idle.png', 8, W, H),
        }

    def update(self, target, arrows_list, controls,):
        if self.is_dead: 
            self.update_animation()
            return

        keys = pygame.key.get_pressed()

        if not self.is_attacking and self.state != 'hit':
            # Ruch
            if keys[controls['left']]: 
                self.rect.x -= (self.vel * 0.8) # Golem jest nieco wolniejszy
                self.direction = 'left'
                if not self.is_jumping: self.state = 'walk'
            elif keys[controls['right']]: 
                self.rect.x += (self.vel * 0.8)
                self.direction = 'right'
                if not self.is_jumping: self.state = 'walk'
            else:
                if not self.is_jumping: self.state = 'idle'
            
            # Skok
            if keys[controls['jump']] and not self.is_jumping:
                self.vel_y = self.jump_height
                self.is_jumping = True
                self.state = 'jump'
                self.frame_index = 0
            
            # Atak
            if keys[controls['atk1']] or keys[controls['atk2']]: 
                self.state = 'attack1'
                self.is_attacking = True
                self.frame_index = 0

        self.apply_gravity(platforms)
        self.update_hitbox()
        self.check_attack_collision(target)
        
        if self.hit_cooldown > 0: self.hit_cooldown -= 1
        self.update_animation()


class HumanSoldier(Character):
    def __init__(self, x, y):
        # Ścieżka do Twoich nowych plików 96x96
        folder_path = "Assets/Human_Soldier_Sword_Shield"
        super().__init__(x, y, folder_path, scale=2.5, hp=100, speed=6, damage=12)
        self.image_offset_y = 100 # Przykładowa wartość - zwiększaj, jeśli nadal lewituje
        # Wymiary klatki to 96x96
        W, H = 96, 96
        
        self.animations = {
            'idle':    self.load_sheet('Human_Soldier_Sword_Shield_Idle-Sheet.png', 6, W, H),
            'walk':    self.load_sheet('Human_Soldier_Sword_Shield_Walk-Sheet.png', 8, W, H),
            'jump':    self.load_sheet('Human_Soldier_Sword_Shield_Jump_Fall-Sheet.png', 5, W, H),
            'attack1': self.load_sheet('Human_Soldier_Sword_Shield_Attack1-Sheet.png', 8, W, H),
            'attack2': self.load_sheet('Human_Soldier_Sword_Shield_Attack2-Sheet.png', 8, W, H),
            'block':   self.load_sheet('Human_Soldier_Sword_Shield_Block-Sheet.png', 6, W, H),
            'hit':     self.load_sheet('Human_Soldier_Sword_Shield_Hurt-Sheet.png', 4, W, H),
            'death':   self.load_sheet('Human_Soldier_Sword_Shield_Death-Sheet.png', 10, W, H),
        }

    def update(self, target, arrows_list, controls):
        if self.is_dead: 
            self.update_animation()
            return

        keys = pygame.key.get_pressed()

        # Rycerz ma dedykowaną animację bloku
        self.is_blocking = keys[controls['block']] and not self.is_jumping and not self.is_attacking
        
        if self.is_blocking:
            self.state = 'block'
        elif not self.is_attacking and self.state != 'hit':
            # Ruch
            if keys[controls['left']]: 
                self.rect.x -= self.vel
                self.direction = 'left'
                if not self.is_jumping: self.state = 'walk'
            elif keys[controls['right']]: 
                self.rect.x += self.vel
                self.direction = 'right'
                if not self.is_jumping: self.state = 'walk'
            else:
                if not self.is_jumping: self.state = 'idle'
            
            # Skok
            if keys[controls['jump']] and not self.is_jumping:
                self.vel_y = self.jump_height
                self.is_jumping = True
                self.state = 'jump'
                self.frame_index = 0
            
            # Ataki
            if keys[controls['atk1']]: 
                self.state = 'attack1'; self.is_attacking = True; self.frame_index = 0
            elif keys[controls['atk2']]: 
                self.state = 'attack2'; self.is_attacking = True; self.frame_index = 0

        self.apply_gravity(platforms)
        self.update_hitbox()
        self.check_attack_collision(target)
        
        if self.hit_cooldown > 0: self.hit_cooldown -= 1
        self.update_animation()

# --- KLASY POSTACI ---
class Soldier(Character):
    def __init__(self, x, y):
        # Upewnij się, że folder "Assets" ma dużą literę, jeśli tak masz na dysku
        super().__init__(x, y, "Assets/Soldier", hp=100, speed=6, damage=12)
        self.animations = {
            'idle': self.load_sheet('Soldier_Idle.png', 6, 100, 100),
            'walk': self.load_sheet('Soldier_Walk.png', 8, 100, 100),
            'jump': self.load_sheet('Soldier_Jump.png', 7, 100, 100),
            'attack1': self.load_sheet('Soldier_Attack01.png', 6, 100, 100),
            'attack2': self.load_sheet('Soldier_Attack02.png', 6, 100, 100),
            'bow': self.load_sheet('Soldier_Attack03_No_Special_Effects.png', 9, 100, 100),
            'hit': self.load_sheet('Soldier_Hit.png', 5, 100, 100),
            'death': self.load_sheet('Soldier_Death.png', 4, 100, 100),
        }
        self.arrow_shot = False
        self.image_offset_y = 110
    def update(self, target, arrows_list, controls):
        # 1. Jeśli martwy - tylko animacja i koniec
        if self.is_dead: 
            self.update_animation()
            return

        keys = pygame.key.get_pressed()

        # 2. Sterowanie - zablokowane podczas ataku LUB podczas otrzymywania obrażeń (hit)
        if not self.is_attacking and self.state != 'hit':
            # Ruch lewo/prawo
            if keys[controls['left']]: 
                self.rect.x -= self.vel
                self.direction = 'left'
                if not self.is_jumping: self.state = 'walk'
            elif keys[controls['right']]: 
                self.rect.x += self.vel
                self.direction = 'right'
                if not self.is_jumping: self.state = 'walk'
            else:
                if not self.is_jumping: self.state = 'idle'
            
            # Skok
            if keys[controls['jump']] and not self.is_jumping:
                self.vel_y = self.jump_height
                self.is_jumping = True
                self.state = 'jump'
                self.frame_index = 0
            
            # Ataki
            if keys[controls['atk1']]: 
                self.state = 'attack1'; self.is_attacking = True; self.frame_index = 0
            elif keys[controls['atk2']]: 
                self.state = 'attack2'; self.is_attacking = True; self.frame_index = 0
            elif keys[controls['special']]: 
                self.state = 'bow'; self.is_attacking = True; self.frame_index = 0; self.arrow_shot = False

        # 3. Mechanika strzału (musi być poza sterowaniem)
        if self.state == 'bow' and int(self.frame_index) == 6 and not self.arrow_shot:
            sp_x = self.hitbox.right if self.direction == 'right' else self.hitbox.left
            arrows_list.append(Arrow(sp_x, self.hitbox.centery +25, self.direction, self)) 
            self.arrow_shot = True

        # 4. Fizyka i Hitboxy (zawsze aktywne)
        # Wewnątrz Orc.update oraz Soldier.update
        self.apply_gravity(platforms)
        self.update_hitbox()
        self.check_attack_collision(target)
        
        if self.hit_cooldown > 0: 
            self.hit_cooldown -= 1
            
        # 5. Aktualizacja klatek animacji
        self.update_animation()
class Orc(Character):
    def __init__(self, x, y):
        super().__init__(x, y, "Assets/Orc", hp=100, speed=6, damage=12)
        self.image_offset_y = 110
        self.animations = {
            'idle': self.load_sheet('Orc_Idle.png', 6, 100, 100),
            'walk': self.load_sheet('Orc_Walk.png', 8, 100, 100),
            'jump': self.load_sheet('Orc_Jump.png', 7, 100, 100),
            'attack1': self.load_sheet('Orc_Attack01.png', 6, 100, 100),
            'attack2': self.load_sheet('Orc_Attack02.png', 6, 100, 100),
            'block': self.load_sheet('Orc_Defense.png', 3, 100, 100),
            'hit': self.load_sheet('Orc_Hit.png', 5, 100, 100),
            'death': self.load_sheet('Orc_Death.png', 4, 100, 100),
        }

    def update(self, target, arrows_list, controls):
        # 1. Jeśli martwy, tylko animacja śmierci
        if self.is_dead: 
            self.update_animation()
            return

        keys = pygame.key.get_pressed()

        # 2. LOGIKA RUCHU I ATAKU (blokowana przez 'hit' i 'attacking')
        # Postać nie może zacząć iść ani atakować, jeśli właśnie obrywa (hit)
        if not self.is_attacking and self.state != 'hit':
            self.is_blocking = keys[controls['block']] and not self.is_jumping
            
            if self.is_blocking:
                self.state = 'block'
            else:
                # Ruch lewo/prawo
                if keys[controls['left']]:
                    self.rect.x -= self.vel
                    self.direction = 'left'
                    if not self.is_jumping: self.state = 'walk'
                elif keys[controls['right']]:
                    self.rect.x += self.vel
                    self.direction = 'right'
                    if not self.is_jumping: self.state = 'walk'
                else:
                    if not self.is_jumping: self.state = 'idle'
                
                # Skok
                if keys[controls['jump']] and not self.is_jumping:
                    self.vel_y = self.jump_height
                    self.is_jumping = True
                    self.state = 'jump'
                    self.frame_index = 0
                
                # Ataki (Tylko jeśli nie blokuje)
                if keys[controls['atk1']]:
                    self.state = 'attack1'; self.is_attacking = True; self.frame_index = 0
                elif keys[controls['atk2']]:
                    self.state = 'attack2'; self.is_attacking = True; self.frame_index = 0
                # Specjalny dla Soldier
                elif 'special' in controls and keys[controls['special']]:
                    if hasattr(self, 'arrow_shot'): # Sprawdzenie czy to Soldier
                        self.state = 'bow'; self.is_attacking = True; self.frame_index = 0; self.arrow_shot = False

        # 3. FIZYKA I ANIMACJA (zawsze poza powyższym IF-em)
        # Dzięki temu grawitacja działa nawet jak postać dostaje hit
    
        self.apply_gravity(platforms)
        self.update_hitbox()
        self.check_attack_collision(target)
        
        if self.hit_cooldown > 0: 
            self.hit_cooldown -= 1
            
        self.update_animation()

async def main():
    global game_state, menu_index, p1_char_index, p2_char_index, game_mode
    global player1, player2, P1_CONTROLS, P2_CONTROLS, is_binding, setting_selected_idx
    global selected_map_index # Dodaj to do globalnych na początku funkcji
    bind_list = [
        ("P1", "Atak 1", "atk1"), ("P1", "Atak 2", "atk2"), ("P1", "Specjalny", "special"), ("P1", "Blok", "block"),
        ("P2", "Atak 1", "atk1"), ("P2", "Atak 2", "atk2"), ("P2", "Specjalny", "special"), ("P2", "Blok", "block")
    ]

    
    # Previews dla Menu Wyboru
    p1_pre_soldier = Soldier(200, 150); p1_pre_orc = Orc(200, 150); p1_pre_knight = HumanSoldier(200, 150); p1_pre_golem = Golem(200, 150)
    p2_pre_soldier = Soldier(650, 150); p2_pre_orc = Orc(650, 150); p2_pre_knight = HumanSoldier(650, 150); p2_pre_golem = Golem(650, 150)
    # Stwórz listy podglądu raz
    p1_previews = [p1_pre_soldier, p1_pre_orc, p1_pre_knight, p1_pre_golem]
    p2_previews = [p2_pre_soldier, p2_pre_orc, p2_pre_knight, p2_pre_golem]

    # Kierunki dla podglądu
    for p in [p1_pre_soldier, p1_pre_orc, p1_pre_knight, p1_pre_golem]: p.direction = 'right'
    for p in [p2_pre_soldier, p2_pre_orc, p2_pre_knight, p2_pre_golem]: p.direction = 'left'

    arrows = []
    potions = []
    potion_spawn_timer = 0
    POTION_SPAWN_COOLDOWN = 400 # ok. 8 sekund przy 50 FPS   
     
    run = True
    
    while run:
        screen.fill((30, 30, 30))
        events = pygame.event.get()
        all_targets = [player1, player2] + cpu_enemies
        for event in events:
            if event.type == pygame.QUIT:
                run = False
            
            if event.type == pygame.KEYDOWN:
                # 1. MENU GŁÓWNE
                if game_state == STATE_MENU:
                    if event.key == pygame.K_UP:
                        menu_index = (menu_index - 1) % len(menu_options)
                    elif event.key == pygame.K_DOWN:
                        menu_index = (menu_index + 1) % len(menu_options)
                    elif event.key == pygame.K_RETURN:
                        if menu_index == 0: 
                            game_mode = "single"; game_state = STATE_CHAR_SELECT
                        elif menu_index == 1: 
                            game_mode = "multi"; game_state = STATE_CHAR_SELECT
                        elif menu_index == 2: 
                            game_state = STATE_SETTINGS

                # 2. USTAWIENIA (BINDY)
                elif game_state == STATE_SETTINGS:
                    if is_binding:
                        p_idx, label, action = bind_list[setting_selected_idx]
                        if p_idx == "P1": P1_CONTROLS[action] = event.key
                        else: P2_CONTROLS[action] = event.key
                        is_binding = False
                    else:
                        if event.key == pygame.K_UP:
                            setting_selected_idx = (setting_selected_idx - 1) % len(bind_list)
                        elif event.key == pygame.K_DOWN:
                            setting_selected_idx = (setting_selected_idx + 1) % len(bind_list)
                        elif event.key == pygame.K_RETURN:
                            is_binding = True
                        elif event.key == pygame.K_ESCAPE:
                            game_state = STATE_MENU

                # 3. WYBÓR POSTACI (DODANY ESC)
                elif game_state == STATE_CHAR_SELECT:
                    if event.key == pygame.K_ESCAPE:
                        game_state = STATE_MENU
                        
                    if event.key == pygame.K_a: p1_char_index = (p1_char_index - 1) % 4
                    if event.key == pygame.K_d: p1_char_index = (p1_char_index + 1) % 4
                    if event.key == pygame.K_LEFT: p2_char_index = (p2_char_index - 1) % 4
                    if event.key == pygame.K_RIGHT: p2_char_index = (p2_char_index + 1) % 4
                                        
                    if event.key == pygame.K_RETURN:
                        def spawn(name, x, y):
                            if name == "Soldier": return Soldier(x, y)
                            if name == "Orc": return Orc(x, y)
                            if name == "Knight": return HumanSoldier(x, y)
                            if name == "Golem": return Golem(x, y)
                            return Soldier(x, y)
                    
                        player1 = spawn(available_chars[p1_char_index], 100, 250)
                        player2 = spawn(available_chars[p2_char_index], 700, 250)
                        player2.direction = 'left'; player1.direction = 'right'
                        
                        if game_mode == "single":
                            # LOSOWANIE MAPY NA START SINGLE
                            current_level = random.choice(single_levels)
                            build_platforms(current_level["data"])
                            try:
                                bg_img = pygame.image.load(get_path(current_level["bg_path"])).convert()
                                current_bg_img = pygame.transform.scale(bg_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
                            except: current_bg_img = None
                            arrows = []; potions = []
                            game_state = STATE_PLAYING
                        else:
                            game_state = STATE_MAP_SELECT

                # 4. WYBÓR MAPY (Tylko Multi)
                elif game_state == STATE_MAP_SELECT:
                    if event.key == pygame.K_ESCAPE: game_state = STATE_CHAR_SELECT
                    maps_to_show = available_maps
                    if event.key in [pygame.K_LEFT, pygame.K_a]: selected_map_index = (selected_map_index - 1) % len(maps_to_show)
                    if event.key in [pygame.K_RIGHT, pygame.K_d]: selected_map_index = (selected_map_index + 1) % len(maps_to_show)
                    if event.key == pygame.K_RETURN:
                        map_info = maps_to_show[selected_map_index]
                        build_platforms(map_info["data"])
                        try:
                            raw_bg = pygame.image.load(get_path(map_info["bg_path"])).convert()
                            current_bg_img = pygame.transform.scale(raw_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
                        except: current_bg_img = None
                        player1.rect.x, player1.rect.y = 100, 250
                        player2.rect.x, player2.rect.y = 700, 250
                        arrows = []; potions = []; game_state = STATE_PLAYING

                # 5. LOGIKA W TRAKCIE GRY (KLIKANIE ENTER)
                elif game_state == STATE_PLAYING:
                    if event.key == pygame.K_ESCAPE: game_state = STATE_MENU
                    
                    # Restart po śmierci lub NOWY POZIOM w Single
                    if event.key == pygame.K_RETURN:
                        if player1.is_dead or (game_mode == "multi" and player2.is_dead):
                            game_state = STATE_MENU
                        elif game_mode == "single" and len(cpu_enemies) == 0:
                            # --- ŁADOWANIE KOLEJNEJ LOSOWEJ MAPY ---
                            next_level = random.choice(single_levels)
                            build_platforms(next_level["data"])
                            try:
                                bg_img = pygame.image.load(get_path(next_level["bg_path"])).convert()
                                current_bg_img = pygame.transform.scale(bg_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
                            except: pass
                            player1.rect.x, player1.rect.y = 100, 250
                            player1.current_hp = min(player1.current_hp + 30, player1.max_hp) # Bonus HP
                            arrows.clear(); potions.clear()
 

        # --- RENDEROWANIE ---
        if game_state == STATE_MENU:
            title = font_main.render("Przystań Fight Game", True, (255, 215, 0))
            screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
            for i, opt in enumerate(menu_options):
                draw_keyboard_button(opt, 350, 180 + i*80, 300, 60, i == menu_index)

        elif game_state == STATE_CHAR_SELECT:
            label = font_sub.render("Wybór: [A/D] P1, [Strzałki] P2, [ENTER] Start", True, (255, 255, 255))
            screen.blit(label, (SCREEN_WIDTH // 2 - label.get_width()//2, 50))
            
            # --- POPRAWIONA LOGIKA WYBORU PODGLĄDU ---
            # --- LOGIKA WYBORU PODGLĄDU ---
            def get_preview(idx, p_list):
                return p_list[idx]
            
            # Pobieraj z gotowej listy zamiast tworzyć nową
            p1_v = p1_previews[p1_char_index]
            p2_v = p2_previews[p2_char_index]
            
            p1_v.update_animation()
            p2_v.update_animation()
            
            # --- DYNAMICZNE DOPASOWANIE WYSOKOŚCI ---
            # Jeśli postać to Golem (index 3), zostawiamy 330. Dla reszty obniżamy postać (np. do 380).
            # Wartość 380 możesz dostosować (zwiększyć), aż postacie dotkną ziemi.
            y_pos_p1 = 330 if p1_char_index == 3 else 420
            y_pos_p2 = 330 if p2_char_index == 3 else 420
            
            p1_rect = p1_v.image.get_rect(midbottom=(250, y_pos_p1))
            p2_rect = p2_v.image.get_rect(midbottom=(750, y_pos_p2))
            
            screen.blit(p1_v.image, p1_rect)
            screen.blit(p2_v.image, p2_rect)
                        
            p1_name = font_sub.render(f"P1: {available_chars[p1_char_index]}", True, (100, 100, 255))
            p2_name = font_sub.render(f"P2: {available_chars[p2_char_index]}", True, (255, 100, 100))
            screen.blit(p1_name, (220, 350)); screen.blit(p2_name, (670, 350))
            
            hint = font_sub.render("ESC - Powrót", True, (150, 150, 150))
            screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, 460))


        elif game_state == STATE_MAP_SELECT:
            # Tytuł
            title = font_main.render("WYBIERZ ARENĘ", True, (255, 255, 255))
            screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 80))
            
            # Nazwa aktualnie wybranej mapy
            map_name = available_maps[selected_map_index]["name"]
            map_info = font_main.render(f"<  {map_name}  >", True, (255, 215, 0))
            screen.blit(map_info, (SCREEN_WIDTH//2 - map_info.get_width()//2, 220))
            
            # Instrukcja
            hint = font_sub.render("A / D lub Strzałki - Zmiana, ENTER - Walcz!", True, (200, 200, 200))
            screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, 350))
            
            back_hint = font_sub.render("ESC - Powrót do postaci", True, (150, 150, 150))
            screen.blit(back_hint, (SCREEN_WIDTH//2 - back_hint.get_width()//2, 450))


        elif game_state == STATE_SETTINGS:
            header = font_main.render("USTAWIENIA KLAWISZY", True, (255, 255, 255))
            screen.blit(header, (SCREEN_WIDTH//2 - header.get_width()//2, 30))
            for i, (p_idx, label, action) in enumerate(bind_list):
                current_controls = P1_CONTROLS if p_idx == "P1" else P2_CONTROLS
                try:
                    k_val = current_controls[action]
                    key_name = pygame.key.name(k_val).upper()
                except:
                    key_name = "???"
                text = f"{p_idx} {label}: {key_name}"
                if is_binding and i == setting_selected_idx:
                    text = f"{p_idx} {label}: <WCIŚNIJ KLAWISZ>"
                draw_keyboard_button(text, 250, 100 + i * 45, 500, 35, i == setting_selected_idx)
            
            hint = font_sub.render("ESC - Powrót", True, (150, 150, 150))
            screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, 460))

        elif game_state == STATE_PLAYING:
            # 1. TŁO I ARENA
            if current_bg_img: screen.blit(current_bg_img, (0, 0))
            for row_idx, row in enumerate(game_map):
                for col_idx, tile_idx in enumerate(row):
                    if tile_idx != 'B' and isinstance(tile_idx, int):
                        screen.blit(tiles[tile_idx], (col_idx * TILE_SIZE, row_idx * TILE_SIZE))

            # --- LOGIKA POSTACI ---

            # 2. AKTUALIZACJA POSTACI
            if game_mode == "multi":
                all_characters = [player1, player2]
                player1.update(player2, arrows, P1_CONTROLS)
                player2.update(player1, arrows, P2_CONTROLS)
            else:
                # SINGLE PLAYER
                all_characters = [player1] + cpu_enemies
                player1.update(cpu_enemies, arrows, P1_CONTROLS)
                for enemy in cpu_enemies[:]:
                    enemy.update_cpu(player1, arrows)
                    # Sprawdzanie czy wróg ostatecznie zniknął (po animacji śmierci)
                    if enemy.is_dead and int(enemy.frame_index) >= len(enemy.animations['death']) - 1:
                        cpu_enemies.remove(enemy)

                # --- MECHANIZM RANDOMOWEJ MAPY PO POKONANIU WROGÓW ---
                if len(cpu_enemies) == 0 and not player1.is_dead:
                    # Wybieramy nową mapę (inną niż obecna, jeśli masz ich więcej)
                    next_level = random.choice(single_levels)
                    build_platforms(next_level["data"])
                    
                    # Ładujemy nowe tło
                    try:
                        bg_img = pygame.image.load(get_path(next_level["bg_path"])).convert()
                        current_bg_img = pygame.transform.scale(bg_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    except: pass
                    
                    # Resetujemy pozycję gracza na start nowej mapy
                    player1.rect.x, player1.rect.y = 100, 250
                    # Opcjonalnie: ulecz gracza o 20 HP za wygraną
                    player1.current_hp = min(player1.current_hp + 20, player1.max_hp)
            # --- TELEPORTACJA I RENDEROWANIE ---
            # --- TELEPORTACJA I RENDEROWANIE ---
            # --- TELEPORTACJA I RENDEROWANIE ---
            # --- TELEPORTACJA I RENDEROWANIE ---
            margin = 2
            offset = 10
            
            # Tworzymy kopię listy, aby uniknąć błędów przy usuwaniu wrogów w trakcie pętli
            render_list = [p for p in all_characters if p is not None]

            for p in render_list:
                # 1. Logika teleportacji
                try:
                    if p.rect.right > SCREEN_WIDTH - margin:
                        p.rect.x = offset
                    elif p.rect.left < margin:
                        p.rect.x = SCREEN_WIDTH - p.rect.width - offset
                except: pass
                
                # 2. Rysowanie grafiki postaci
                off_y = getattr(p, 'image_offset_y', 0)
                img_rect = p.image.get_rect(midbottom=(p.rect.centerx, p.rect.bottom + off_y))
                screen.blit(p.image, img_rect)

                # 3. PASEK HP NAD PRZECIWNIKAMI (Tylko Single Player)
                # Sprawdzamy czy to nie Gracz 1 i czy to nie Gracz 2
                is_p1 = (p == player1)
                is_p2 = (game_mode == "multi" and p == player2)
                
                if not is_p1 and not is_p2 and not getattr(p, 'is_dead', False):
                    # Pobieramy bezpiecznie wartości
                    curr_h = getattr(p, 'current_hp', 0)
                    max_h = getattr(p, 'max_hp', 0)
                    
                    if max_h > 0:
                        bar_w = 40
                        bar_h = 5
                        # Pozycjonowanie (p.rect musi istnieć)
                        bx = p.rect.centerx - bar_w // 2
                        by = p.rect.top - 15
                        
                        # Rysowanie tła i życia
                        pygame.draw.rect(screen, (100, 0, 0), (bx, by, bar_w, bar_h))
                        fill_w = int(bar_w * max(0, min(curr_h / max_h, 1)))
                        pygame.draw.rect(screen, (0, 255, 0), (bx, by, fill_w, bar_h))
                        pygame.draw.rect(screen, (0, 0, 0), (bx, by, bar_w, bar_h), 1)
            # --- POCISKI I POTKI ---
            for pot in potions[:]:
                if pot.update(platforms, all_characters): potions.remove(pot)
                else: screen.blit(pot.image, pot.rect)

            # --- Wewnątrz pętli gry (while True) ---

            # 1. Przygotuj listę celów (wszyscy, którzy mogą dostać strzałą)
            all_targets = [player1, player2] + cpu_enemies
            
            # --- POPRAWIONA LOGIKA STRZAŁ ---
            # 1. Przygotuj listę celów
            all_targets = [player1, player2] + cpu_enemies
            
            # 2. Aktualizuj każdą strzałę
            # Używamy nazwy 'arrows', bo taką zdefiniowałeś na początku funkcji main
            for arrow in arrows:
                arrow.update(all_targets)
            
            # 3. Bezpieczne usuwanie nieaktywnych strzał (Filtrowanie)
            arrows[:] = [a for a in arrows if a.active]
            
            # 4. Rysowanie
            for arrow in arrows:
                screen.blit(arrow.image, arrow.rect)

            # --- INTERFEJS (HUD) ---
            player1.draw_hp_bar(screen, 20, 20)
            
            if game_mode == "multi":
                player2.draw_hp_bar(screen, SCREEN_WIDTH - 20, 20, align_right=True)
                if player1.is_dead or player2.is_dead:
                    msg = "PLAYER 1 WYGRAŁ!" if player2.is_dead else "PLAYER 2 WYGRAŁ!"
                    txt = font_main.render(msg, True, (255, 255, 255))
                    screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 200))
            else:
                # Nagłówki Single Player
                enemies_left = len(cpu_enemies)
                count_txt = font_sub.render(f"Przeciwnicy: {enemies_left}", True, (255, 100, 100))
                screen.blit(count_txt, (SCREEN_WIDTH - 150, 20))
                
                if enemies_left == 0:
                    win_txt = font_main.render("POZIOM UKOŃCZONY!", True, (0, 255, 0))
                    screen.blit(win_txt, (SCREEN_WIDTH//2 - win_txt.get_width()//2, 200))
                    hint_txt = font_sub.render("Naciśnij ENTER aby kontynuować", True, (200, 200, 200))
                    screen.blit(hint_txt, (SCREEN_WIDTH//2 - hint_txt.get_width()//2, 280))
                elif player1.is_dead:
                    lose_txt = font_main.render("ZGINĄŁEŚ!", True, (255, 0, 0))
                    screen.blit(lose_txt, (SCREEN_WIDTH//2 - lose_txt.get_width()//2, 200))

            # Spawn potyczek
            potion_spawn_timer += 1
            if potion_spawn_timer >= POTION_SPAWN_COOLDOWN:
                potions.append(HealthPotion(random.randint(100, SCREEN_WIDTH-100), -50))
                potion_spawn_timer = 0
        pygame.display.flip()
        clock.tick(50)
        await asyncio.sleep(0)
# Start
asyncio.run(main())
