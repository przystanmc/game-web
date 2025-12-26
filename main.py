import pygame
import asyncio

pygame.init()
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 500
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

pygame.font.init()
font_main = pygame.font.SysFont('Arial', 50)
font_sub = pygame.font.SysFont('Arial', 30)

# Stany gry
STATE_MENU = "menu"
STATE_CHAR_SELECT = "char_select"
STATE_OPTIONS = "options"
STATE_PLAYING = "playing"
game_state = STATE_MENU

# Wybory graczy
game_mode = "multi" # lub "single"
p1_choice = "Soldier"
p2_choice = "Orc"
# --- FUNKCJA RYSUJĄCA PRZYCISK ---
def draw_button(text, x, y, width, height, active_color, inactive_color):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed(num_buttons=3)

    
    rect = pygame.Rect(x, y, width, height)
    is_hovered = rect.collidepoint(mouse)
    
    color = active_color if is_hovered else inactive_color
    pygame.draw.rect(screen, color, rect, border_radius=10)
    
    text_surf = font_sub.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)
    
    return is_hovered and click[0]
# --- KLASA POCISKU ---
class Arrow(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner): # Dodajemy owner
        super().__init__()
        self.owner = owner # Zapamiętujemy, kto strzelił
        self.speed = 12
        self.image = pygame.Surface((20, 4))
        self.image.fill((200, 200, 200))
        self.rect = self.image.get_rect()
        
        if direction == 'right':
            self.rect.left = x
            self.vel = self.speed
        else:
            self.rect.right = x
            self.vel = -self.speed
            self.image = pygame.transform.flip(self.image, True, False)
            
        self.rect.centery = y
        self.damage = 15

    def update(self, player1, player2, arrows_list): # Teraz przyjmuje obu graczy
        self.rect.x += self.vel
        
        # Ustalamy, kto jest celem (ten, kto nie jest właścicielem)
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
        self.rect = pygame.Rect(x, y, 100 * scale, 100 * scale)
        self.hitbox = pygame.Rect(x, y, 45, 55)
        self.vel_y = 0
        self.gravity = 0.8
        self.jump_height = -16
        self.is_jumping = False
        self.ground_y = y  # Zapamiętujemy poziom ziemi

    def load_sheet(self, filename, frame_count, width, height):
        path = f"{self.folder}/{filename}"
        try:
            sheet = pygame.image.load(path).convert_alpha()
            frames = []
            for i in range(frame_count):
                frame = sheet.subsurface((i * width, 0, width, height))
                frame = pygame.transform.scale(frame, (int(width * self.scale), int(height * self.scale)))
                frames.append(frame)
            return frames
        except:
            surf = pygame.Surface((50, 50)); surf.fill((100, 0, 0))
            return [surf]

    def update_hitbox(self):
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.centery = self.rect.centery - 5
        
    def take_damage(self, amount):
        if not self.is_dead and not self.is_blocking:
            self.current_hp -= amount
            if self.current_hp <= 0:
                self.current_hp = 0
                self.is_dead = True
                self.state = 'death'
            else:
                self.state = 'hit'
            self.frame_index = 0

    def draw_hp_bar(self, surface, x, y, align_right=False):
        bar_width = 300
        bar_height = 25
        
        # Obliczamy szerokość zielonego paska na podstawie HP
        hp_width = int(bar_width * (self.current_hp / self.max_hp))
        
        if align_right:
            # Pasek dla gracza po prawej (Orka)
            # Rysujemy tło (czerwone)
            pygame.draw.rect(surface, (255, 0, 0), (x - bar_width, y, bar_width, bar_height))
            # Rysujemy aktualne HP (zielone) - wyrównane do prawej
            pygame.draw.rect(surface, (0, 255, 0), (x - hp_width, y, hp_width, bar_height))
            # Ramka
            pygame.draw.rect(surface, (255, 255, 255), (x - bar_width, y, bar_width, bar_height), 2)
        else:
            # Pasek dla gracza po lewej (Soldier)
            pygame.draw.rect(surface, (255, 0, 0), (x, y, bar_width, bar_height))
            pygame.draw.rect(surface, (0, 255, 0), (x, y, hp_width, bar_height))
            pygame.draw.rect(surface, (255, 255, 255), (x, y, bar_width, bar_height), 2)

    def update_animation(self):
        # 1. Wybór odpowiednich klatek
        if self.is_dead:
            frames = self.animations['death']
            self.frame_index = min(self.frame_index + 0.15, len(frames) - 1)
        elif self.state == 'block' and self.is_blocking:
            frames = self.animations['block']
            self.frame_index = min(self.frame_index + 0.15, len(frames) - 1)
        else:
            frames = self.animations.get(self.state, self.animations['idle'])
            
            # Prędkość animacji
            if self.state == 'jump':
                anim_speed = 0.15
            elif self.is_attacking:
                anim_speed = 0.25
            else:
                anim_speed = 0.18
                
            self.frame_index += anim_speed

            # Zapętlanie lub kończenie animacji
            if self.frame_index >= len(frames):
                if self.is_attacking or self.state == 'hit':
                    self.is_attacking = False
                    self.state = 'idle'
                self.frame_index = 0

        # 2. Renderowanie obrazu
        self.image = frames[int(self.frame_index)]
        if self.direction == 'left':
            self.image = pygame.transform.flip(self.image, True, False)
            
    def apply_gravity(self):
        self.vel_y += self.gravity
        self.rect.y += self.vel_y
        
        # Kolizja z ziemią
        if self.rect.y >= self.ground_y:
            self.rect.y = self.ground_y
            self.vel_y = 0
            self.is_jumping = False
            if self.state == 'jump':
                self.state = 'idle'


    def check_attack_collision(self, target):
        if self.is_attacking and self.state != 'bow' and 3 <= int(self.frame_index) <= 4:
            attack_rect = pygame.Rect(0, 0, 30, 40)
            if self.direction == 'right': attack_rect.left = self.hitbox.right
            else: attack_rect.right = self.hitbox.left
            attack_rect.centery = self.hitbox.centery

            if attack_rect.colliderect(target.hitbox) and target.hit_cooldown == 0:
                target.take_damage(10)
                target.hit_cooldown = 30
    def screen_wrap(self):
        # Jeśli środek postaci wyjdzie poza prawą krawędź
        if self.rect.centerx > SCREEN_WIDTH:
            self.rect.centerx = 0
        # Jeśli środek postaci wyjdzie poza lewą krawędź
        elif self.rect.centerx < 0:
            self.rect.centerx = SCREEN_WIDTH


# --- KLASY KONKRETNE ---
class Soldier(Character):
    def __init__(self, x, y):
        super().__init__(x, y, "Soldier")
        self.animations = {
            'idle': self.load_sheet('Soldier_Idle.png', 6, 100, 100),
            'walk': self.load_sheet('Soldier_Walk.png', 8, 100, 100),
            'jump': self.load_sheet('Soldier_Jump.png', 7, 100, 100), # Nowa animacja
            'attack1': self.load_sheet('Soldier_Attack01.png', 6, 100, 100),
            'attack2': self.load_sheet('Soldier_Attack02.png', 6, 100, 100),
            'bow': self.load_sheet('Soldier_Attack03_No Special Effects.png', 9, 100, 100),
            'hit': self.load_sheet('Soldier_Hit.png', 5, 100, 100),
            'death': self.load_sheet('Soldier_Death.png', 4, 100, 100),
        }
        self.arrow_shot = False

    def update(self, target, arrows_list, controls): # Dodano controls
        if self.is_dead: 
            self.update_animation()
            return
        # Odwracanie w stronę przeciwnika, gdy postać nie atakuje i nie idzie
        if not self.is_attacking and self.state != 'walk':
            if self.rect.centerx < target.rect.centerx:
                self.direction = 'right'
            else:
                self.direction = 'left'

        keys = pygame.key.get_pressed()
        
        if keys[controls['jump']] and not self.is_jumping:
            self.vel_y = self.jump_height
            self.is_jumping = True
            self.state = 'jump'
            self.frame_index = 0

        if not self.is_attacking and self.state != 'hit':
            if not self.is_jumping: self.state = 'idle'
            
            if keys[controls['left']]: 
                self.rect.x -= self.vel
                self.direction = 'left'
                if not self.is_jumping: self.state = 'walk'
            elif keys[controls['right']]: 
                self.rect.x += self.vel
                self.direction = 'right'
                if not self.is_jumping: self.state = 'walk'
            
            if keys[controls['atk1']]: 
                self.state = 'attack1'; self.is_attacking = True; self.frame_index = 0
            elif keys[controls['atk2']]: 
                self.state = 'attack2'; self.is_attacking = True; self.frame_index = 0
            elif keys[controls['special']]: 
                self.state = 'bow'; self.is_attacking = True; self.frame_index = 0; self.arrow_shot = False

        if self.state == 'bow' and int(self.frame_index) == 6 and not self.arrow_shot:
            spawn_x = self.hitbox.right if self.direction == 'right' else self.hitbox.left
            arrows_list.append(Arrow(spawn_x, self.hitbox.centery, self.direction, self)) 
            self.arrow_shot = True

        self.apply_gravity()
        self.update_hitbox()
        self.check_attack_collision(target)
        if self.hit_cooldown > 0: self.hit_cooldown -= 1
        self.update_animation()




class Orc(Character):
    def __init__(self, x, y):
        super().__init__(x, y, "Orc")
        self.animations = {
            'idle': self.load_sheet('Orc_Idle.png', 6, 100, 100),
            'walk': self.load_sheet('Orc_Walk.png', 8, 100, 100),
            'jump': self.load_sheet('Orc_Jump.png', 7, 100, 100), # Tu Twoja nowa animacja
            'attack1': self.load_sheet('Orc_Attack01.png', 6, 100, 100),
            'attack2': self.load_sheet('Orc_Attack02.png', 6, 100, 100),
            'block': self.load_sheet('Orc_Defense.png', 3, 100, 100),
            'hit': self.load_sheet('Orc_Hit.png', 5, 100, 100),
            'death': self.load_sheet('Orc_Death.png', 4, 100, 100),
        }
        self.direction = 'left'

    def update(self, target, arrows_list, controls): # Dodano controls
        if self.is_dead: 
            self.update_animation()
            return
        # Odwracanie w stronę przeciwnika, gdy postać nie atakuje i nie idzie
        if not self.is_attacking and self.state != 'walk':
            if self.rect.centerx < target.rect.centerx:
                self.direction = 'right'
            else:
                self.direction = 'left'


        keys = pygame.key.get_pressed()
        
        if keys[controls['jump']] and not self.is_jumping and not self.is_blocking:
            self.vel_y = self.jump_height
            self.is_jumping = True
            self.state = 'jump'
            self.frame_index = 0

        # Blokowanie używa teraz klawisza ze słownika
        self.is_blocking = keys[controls['block']] and not self.is_attacking and not self.is_jumping
        
        if self.is_blocking:
            self.state = 'block'
        elif not self.is_attacking and self.state != 'hit':
            if not self.is_jumping: self.state = 'idle'
            
            if keys[controls['left']]:
                self.rect.x -= self.vel
                self.direction = 'left'
                if not self.is_jumping: self.state = 'walk'
            elif keys[controls['right']]:
                self.rect.x += self.vel
                self.direction = 'right'
                if not self.is_jumping: self.state = 'walk'
            
            if keys[controls['atk1']]:
                self.state = 'attack1'; self.is_attacking = True; self.frame_index = 0
            elif keys[controls['atk2']]:
                self.state = 'attack2'; self.is_attacking = True; self.frame_index = 0

        self.apply_gravity()
        self.update_hitbox()
        self.check_attack_collision(target)
        if self.hit_cooldown > 0: self.hit_cooldown -= 1
        self.update_animation()


# --- START GRY ---
P1_CONTROLS = {
    'left': pygame.K_a, 'right': pygame.K_d, 'jump': pygame.K_w,
    'atk1': pygame.K_r, 'atk2': pygame.K_t, 'special': pygame.K_y,
    'block': pygame.K_u # Dodatkowy klawisz dla orka
}

P2_CONTROLS = {
    'left': pygame.K_LEFT, 'right': pygame.K_RIGHT, 'jump': pygame.K_UP,
    'atk1': pygame.K_m, 'atk2': pygame.K_COMMA, 'special': pygame.K_PERIOD,
    'block': pygame.K_l # Dodatkowy klawisz dla orka
}
arrows = []
# Lista dostępnych klas postaci
available_chars = ["Soldier", "Orc"]
p1_char_index = 0
p2_char_index = 1


# Obiekty do podglądu w menu - osobne dla P1 i P2
p1_preview_soldier = Soldier(200, 150)
p1_preview_orc = Orc(200, 150)

p2_preview_soldier = Soldier(600, 150)
p2_preview_orc = Orc(600, 150)

async def main():

    global run, game_state, arrows, player1, player2
    global p1_char_index, p2_char_index, game_mode
    run = True

    while run:
        screen.fill((30, 30, 30))
        pygame.event.pump()

        # --- EVENTS ---
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                run = False

            if game_state == STATE_CHAR_SELECT and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    p1_char_index = (p1_char_index - 1) % len(available_chars)
                if event.key == pygame.K_d:
                    p1_char_index = (p1_char_index + 1) % len(available_chars)
                if game_mode == "multi":
                    if event.key == pygame.K_LEFT:
                        p2_char_index = (p2_char_index - 1) % len(available_chars)
                    if event.key == pygame.K_RIGHT:
                        p2_char_index = (p2_char_index + 1) % len(available_chars)

        # --- STAN: MENU GŁÓWNE ---
        if game_state == STATE_MENU:
            title = font_main.render("FANTASY FIGHTER", True, (255, 215, 0))
            screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
            
            if draw_button("SINGLE PLAYER", 400, 180, 200, 50, (100, 100, 100), (50, 50, 50)):
                game_mode = "single"
                game_state = STATE_CHAR_SELECT
                pygame.time.wait(200)
        
            if draw_button("MULTI PLAYER", 400, 260, 200, 50, (100, 100, 100), (50, 50, 50)):
                game_mode = "multi"
                game_state = STATE_CHAR_SELECT
                pygame.time.wait(200)
        
            if draw_button("QUIT", 400, 340, 200, 50, (150, 50, 50), (100, 0, 0)):
                run = False
        
            # --- STAN: WYBÓR POSTACI ---
        elif game_state == STATE_CHAR_SELECT:
            screen.fill((20, 20, 20))
            label = font_main.render("SELECT YOUR FIGHTER", True, (255, 255, 255))
            screen.blit(label, (SCREEN_WIDTH//2 - label.get_width()//2, 30))
    
            # Podgląd P1
            p1_name = available_chars[p1_char_index]
            p1_view = p1_preview_soldier if p1_name == "Soldier" else p1_preview_orc
            p1_view.is_dead = False # Reset stanu śmierci
            p1_view.direction = 'right'
            p1_view.update_animation()
            screen.blit(p1_view.image, (150, 150))
    
            # Podgląd P2
            p2_name = available_chars[p2_char_index]
            p2_view = p2_preview_soldier if p2_name == "Soldier" else p2_preview_orc
            p2_view.is_dead = False # Reset stanu śmierci
            p2_view.direction = 'left'
            p2_view.update_animation()
            screen.blit(p2_view.image, (600, 150))
    
            # Napisy sterowania
            p1_txt = font_sub.render(f"P1: {p1_name} ", True, (0, 200, 255))
            p2_label = "P2" if game_mode == "multi" else "CPU"
            p2_txt = font_sub.render(f"{p2_label}: {p2_name} ", True, (255, 50, 50))
            screen.blit(p1_txt, (150, 350))
            screen.blit(p2_txt, (600, 350))
    
            if draw_button("BATTLE!", 400, 420, 200, 50, (0, 200, 0), (0, 100, 0)):
                def create_char(name, x, y):
                    return Soldier(x, y) if name == "Soldier" else Orc(x, y)
                player1 = create_char(p1_name, 100, 250)
                player2 = create_char(p2_name, 700, 250)
                player2.direction = 'left'
                arrows = []
                game_state = STATE_PLAYING
                pygame.time.wait(200)
    
        # --- STAN: WALKA ---
        elif game_state == STATE_PLAYING:
            # Aktualizacja postaci
            player1.update(player2, arrows, P1_CONTROLS)
            player2.update(player1, arrows, P2_CONTROLS)
            player1.screen_wrap()
            player2.screen_wrap()
    
            # Aktualizacja strzał
            for arrow in arrows[:]:
                arrow.update(player1, player2, arrows)
                screen.blit(arrow.image, arrow.rect)
    
            # Rysowanie HP i postaci
            player1.draw_hp_bar(screen, 20, 20)
            player2.draw_hp_bar(screen, SCREEN_WIDTH - 20, 20, align_right=True)
            screen.blit(player1.image, player1.rect)
            screen.blit(player2.image, player2.rect)
    
            # Koniec walki
            if player1.is_dead or player2.is_dead:
                winner = "PLAYER 1" if player2.is_dead else "PLAYER 2"
                win_txt = font_main.render(f"{winner} WINS!", True, (255, 255, 255))
                screen.blit(win_txt, (SCREEN_WIDTH//2 - win_txt.get_width()//2, 120))
                
                if draw_button("BACK TO MENU", 400, 220, 200, 50, (100, 100, 100), (50, 50, 50)):
                    game_state = STATE_MENU
                    pygame.time.wait(200)
    
        pygame.display.update()
        clock.tick(30)
        screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.SCALED
        )
        
asyncio.run(main())



