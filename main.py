import pygame
import asyncio
import pygbag
import os 
import random

def get_path(relative_path):
    return os.path.join(os.path.dirname(__file__), relative_path)

player1 = None
player2 = None

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

game_map = [
    [43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43],
    [43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 44, 43, 43, 43, 43],
    [43, 43, 44, 44, 43, 43, 43, 43, 44, 44, 44, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43],
    [43, 43, 43, 43, 43, 44, 43, 43, 43, 44, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43],
    [43, 43, 43, 43, 44, 13, 2, 15, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43], # Platforma
    [43, 43, 43, 43, 43, 43, 47, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43],
    [43, 43, 43, 43, 43, 43, 48, 43, 43, 43, 43, 40, 34, 35, 36, 40, 43, 43, 43, 43, 43], # Platforma
    [43, 43, 43, 43, 43, 44, 48, 43, 43, 43, 43, 40, 44, 43, 43, 40, 43, 43, 43, 43, 43],
    [43, 43, 43, 43, 43, 43, 37, 43, 43, 43, 43, 42, 43, 43, 43, 42, 43, 43, 43, 43, 43],
    [1, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], # Dół 1, 2, 1, 2...
]

# Funkcja budująca kolizje (wywołuj przy starcie walki)
platforms = []
def build_platforms():
    platforms.clear()
    for row_idx, row in enumerate(game_map):
        for col_idx, tile_idx in enumerate(row):
            if tile_idx in COLLISION_TILES:
                # Tworzymy prostokąt kolizji dokładnie tam, gdzie rysujemy kafelek
                new_rect = pygame.Rect(col_idx * TILE_SIZE, row_idx * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                platforms.append(new_rect)

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
        self.rect.centery = y + 20
        if direction == 'right':
            self.rect.left = x
            self.vel = self.speed
        else:
            self.rect.right = x
            self.vel = -self.speed
            self.image = pygame.transform.flip(self.image, True, False)
        self.rect.centery = y
        self.damage = 15

    def update(self, player1, player2, arrows_list):
        self.rect.x += self.vel
        target = player2 if self.owner == player1 else player1
        if self.rect.colliderect(target.hitbox):
            if not target.is_blocking:
                target.take_damage(self.damage)
            if self in arrows_list: arrows_list.remove(self)
        elif self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            if self in arrows_list: arrows_list.remove(self)

# --- KLASA BAZOWA ---
class Character(pygame.sprite.Sprite):
    def __init__(self, x, y, folder, scale=2.5):
        super().__init__()
        self.folder = folder
        self.scale = scale
        self.animations = {}
        self.state = 'idle'
        self.frame_index = 0
        self.direction = 'right'
        self.is_attacking = False
        self.is_blocking = False
        self.vel = 5
        self.max_hp = 100
        self.current_hp = 100
        self.is_dead = False
        self.hit_cooldown = 0
        self.rect = pygame.Rect(x, y, 40, 60) # Rozmiar zbliżony do TILE_SIZE
        self.hitbox = pygame.Rect(x, y, 40, 60)
        self.vel_y = 0
        self.gravity = 0.8
        self.jump_height = -16
        self.is_jumping = False
        self.ground_y = y
        self.image = pygame.Surface((100, 100)) # Placeholder, żeby gra nie wywaliła się przed pierwszym update
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
        # 1. Wybór odpowiedniej listy klatek (frames)
        if self.is_dead:
            frames = self.animations['death']
            # Zatrzymujemy na ostatniej klatce śmierci
            self.frame_index = min(self.frame_index + 0.15, len(frames) - 1)
        elif self.state == 'block' and self.is_blocking:
            if 'block' in self.animations:
                frames = self.animations['block']
                self.frame_index = min(self.frame_index + 0.15, len(frames) - 1)
            else:
                # Jeśli Soldier nie ma animacji bloku, używamy 'idle'
                frames = self.animations['idle']
                self.frame_index = (self.frame_index + 0.18) % len(frames)
        else:
            # Domyślnie bierzemy stan, a jak go nie ma - idle
            frames = self.animations.get(self.state, self.animations['idle'])
            
            anim_speed = 0.25 if (self.is_attacking or self.state == 'hit') else 0.18
            self.frame_index += anim_speed

            if self.frame_index >= len(frames):
                if self.is_attacking or self.state == 'hit':
                    self.is_attacking = False
                    self.state = 'idle'
                self.frame_index = 0 

        # 2. Wyświetlenie klatki
        self.image = frames[int(self.frame_index)]
        
        if self.direction == 'left':
            self.image = pygame.transform.flip(self.image, True, False)
        # --- KLUCZOWE USTAWIENIE OBRAZU ---
        # Pobieramy klatkę z listy na podstawie zaokrąglonego indeksu
        self.image = frames[int(self.frame_index)]
        
        # Odwracanie grafiki w zależności od kierunku
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
    
    def check_attack_collision(self, target):
        # Sprawdzamy stan ataku i czy klatka jest w fazie zamachu (np. od 3 do 5, by być pewnym trafienia)
        if self.is_attacking and self.state in ['attack1', 'attack2'] and 3 <= int(self.frame_index) <= 5:
            # Twoje sprawdzone wymiary
            attack_rect = pygame.Rect(0, 0, 25, 50)
            
            if self.direction == 'right':
                attack_rect.left = self.hitbox.right
            else:
                attack_rect.right = self.hitbox.left
                
            attack_rect.centery = self.hitbox.centery
            

            
            # Logika obrażeń
            if attack_rect.colliderect(target.hitbox) and target.hit_cooldown == 0:
                target.take_damage(10)
                # hit_cooldown na 30 klatek przy 30 FPS to 1 sekunda ochrony
                target.hit_cooldown = 25

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
    def __init__(self):
        super().__init__()
        # Możesz załadować własny obrazek: pygame.image.load("Assets/potion.png")
        self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 0, 0), (12, 12), 10) # Czerwone kółko jako placeholder
        
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(50, SCREEN_WIDTH - 50)
        self.rect.y = -50  # Zaczyna nad ekranem
        self.vel_y = 0
        self.gravity = 0.5
        self.heal_amount = 20

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
        super().__init__(x, y, folder_path, scale=2.8) # Golem może być nieco większy
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

    def update(self, target, arrows_list, controls):
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
        super().__init__(x, y, folder_path, scale=2.5)
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
        super().__init__(x, y, "Assets/Soldier")
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
        super().__init__(x, y, "Assets/Orc")
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
def build_platforms():
    platforms.clear()
    for row_idx, row in enumerate(game_map):
        for col_idx, tile_idx in enumerate(row):
            if tile_idx in COLLISION_TILES:
                # Usunąłem "+ 150", aby mapa pokrywała się z rysowaniem
                new_rect = pygame.Rect(col_idx * TILE_SIZE, row_idx * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                platforms.append(new_rect)

async def main():
    global game_state, menu_index, p1_char_index, p2_char_index, game_mode
    global player1, player2, P1_CONTROLS, P2_CONTROLS, is_binding, setting_selected_idx

    bind_list = [
        ("P1", "Atak 1", "atk1"), ("P1", "Atak 2", "atk2"), ("P1", "Specjalny", "special"), ("P1", "Blok", "block"),
        ("P2", "Atak 1", "atk1"), ("P2", "Atak 2", "atk2"), ("P2", "Specjalny", "special"), ("P2", "Blok", "block")
    ]
    
    # Previews dla Menu Wyboru
    p1_pre_soldier = Soldier(200, 150); p1_pre_orc = Orc(200, 150); p1_pre_knight = HumanSoldier(200, 150); p1_pre_golem = Golem(200, 150)
    p2_pre_soldier = Soldier(650, 150); p2_pre_orc = Orc(650, 150); p2_pre_knight = HumanSoldier(650, 150); p2_pre_golem = Golem(650, 150)
    
    # Kierunki dla podglądu
    for p in [p1_pre_soldier, p1_pre_orc, p1_pre_knight, p1_pre_golem]: p.direction = 'right'
    for p in [p2_pre_soldier, p2_pre_orc, p2_pre_knight, p2_pre_golem]: p.direction = 'left'

    arrows = []
    potions = []
    potion_spawn_timer = 0

    run = True
    
    while run:
        screen.fill((30, 30, 30))
        events = pygame.event.get()
        
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
                    # To sprawia, że ESC wraca do menu
                    if event.key == pygame.K_ESCAPE:
                        game_state = STATE_MENU
                        
                    # Zmień % 2 na % 3
                    if event.key == pygame.K_a: p1_char_index = (p1_char_index - 1) % 4
                    if event.key == pygame.K_d: p1_char_index = (p1_char_index + 1) % 4
                    if event.key == pygame.K_LEFT: p2_char_index = (p2_char_index - 1) % 4
                    if event.key == pygame.K_RIGHT: p2_char_index = (p2_char_index + 1) % 4
                                        
                    if event.key == pygame.K_RETURN:
                        # Funkcja pomocnicza do tworzenia wybranej klasy
                        def spawn(name, x, y):
                            if name == "Soldier": return Soldier(x, y)
                            if name == "Orc": return Orc(x, y)
                            if name == "Knight": return HumanSoldier(x, y)
                            if name == "Golem": return Golem(x, y)
                            return Soldier(x, y)
                    
                        player1 = spawn(available_chars[p1_char_index], 100, 250)
                        player2 = spawn(available_chars[p2_char_index], 700, 250)
                        player2.direction = 'left'          
                
                
                        player1.direction = 'right'
                        arrows = []
                        build_platforms()
                        game_state = STATE_PLAYING
                    if event.key == pygame.K_RETURN:
                        # ... Twoje istniejące przypisania player1, player2 ...
                        arrows = []
                        potions = [] # <-- DODAJ TĘ LINIĘ
                        potion_spawn_timer = 0 # <-- I TĘ
                        build_platforms()
                        game_state = STATE_PLAYING

                # 4. POWRÓT Z WALKI (DODANY ESC)
                elif game_state == STATE_PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        game_state = STATE_MENU
                    if (player1.is_dead or player2.is_dead) and event.key == pygame.K_RETURN:
                        game_state = STATE_MENU
                    

 

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
            
            p1_v = get_preview(p1_char_index, [p1_pre_soldier, p1_pre_orc, p1_pre_knight, p1_pre_golem])
            p2_v = get_preview(p2_char_index, [p2_pre_soldier, p2_pre_orc, p2_pre_knight, p2_pre_golem])
            
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
            # 1. Rysowanie mapy (tło)
            for row_idx, row in enumerate(game_map):
                for col_idx, tile_idx in enumerate(row):
                    if tile_idx < len(tiles):
                        screen.blit(tiles[tile_idx], (col_idx * TILE_SIZE, row_idx * TILE_SIZE))

            # 2. Aktualizacja orientacji i logiki
            player1.face_target(player2)
            player2.face_target(player1)
            player1.update(player2, arrows, P1_CONTROLS)
            
            if game_mode == "single":
                player2.update_cpu(player1, arrows)
            else:
                player2.update(player1, arrows, P2_CONTROLS)

            # 3. JEDYNE RYSOWANIE POSTACI (z offsetem)
            for p in [player1, player2]:
                if p:
                    # To wyrównuje stopy postaci do podłogi (hitboxa)
                    # Upewnij się, że każda klasa ma zdefiniowane self.image_offset_y w __init__
                    off_y = getattr(p, 'image_offset_y', 0)
                    img_rect = p.image.get_rect(midbottom=(p.rect.centerx, p.rect.bottom + off_y))
                    screen.blit(p.image, img_rect)

            # 4. Mikstury i pociski
            for pot in potions[:]:
                consumed = pot.update(platforms, [player1, player2])
                if consumed: potions.remove(pot)
                else: screen.blit(pot.image, pot.rect)

            for a in arrows[:]:
                a.update(player1, player2, arrows)
                screen.blit(a.image, a.rect)

            # 5. Interfejs (HP i napisy)
            player1.draw_hp_bar(screen, 20, 20)
            player2.draw_hp_bar(screen, SCREEN_WIDTH - 20, 20, align_right=True)

            if player1.is_dead or player2.is_dead:
                win_text = "PLAYER 1 Wygrał!" if player2.is_dead else "PLAYER 2 Wygrał!"
                txt = font_main.render(win_text, True, (255, 255, 255))
                screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 200)) 
                        # -------------------------
                        
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)
# Start
asyncio.run(main())
