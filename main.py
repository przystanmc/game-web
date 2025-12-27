import pygame
import asyncio
import pygbag

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

# Wybory i nawigacja menu
menu_options = ["SINGLE PLAYER", "MULTI PLAYER", "QUIT"]
menu_index = 0
game_mode = "multi"
available_chars = ["Soldier", "Orc"]
p1_char_index = 0
p2_char_index = 1

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

# --- KLASA POCISKU ---
class Arrow(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner):
        super().__init__()
        self.owner = owner
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
        self.rect = pygame.Rect(x, y, 100 * scale, 100 * scale)
        self.hitbox = pygame.Rect(x, y, 45, 55)
        self.vel_y = 0
        self.gravity = 0.8
        self.jump_height = -16
        self.is_jumping = False
        self.ground_y = y
        self.image = pygame.Surface((100, 100)) # Placeholder, żeby gra nie wywaliła się przed pierwszym update


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
            surf.fill((200, 0, 0))
            return [surf] * frame_count

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
        if self.is_dead:
            frames = self.animations['death']
            self.frame_index = min(self.frame_index + 0.15, len(frames) - 1)
        elif self.state == 'block' and self.is_blocking:
            frames = self.animations['block']
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
        
        # --- TA LINIA JEST KLUCZOWA ---
        self.image = frames[int(self.frame_index)]
        
        # Dodatkowo, jeśli postać patrzy w lewo, musimy obrócić obrazek:
        if self.direction == 'left':
            self.image = pygame.transform.flip(self.image, True, False)  
    def apply_gravity(self):
        self.vel_y += self.gravity
        self.rect.y += self.vel_y
        if self.rect.y >= self.ground_y:
            self.rect.y = self.ground_y
            self.vel_y = 0
            self.is_jumping = False
            if self.state == 'jump': self.state = 'idle'

    def check_attack_collision(self, target):
        if self.is_attacking and self.state != 'bow' and 3 <= int(self.frame_index) <= 4:
            att_rect = pygame.Rect(0, 0, 40, 40)
            if self.direction == 'right': att_rect.left = self.hitbox.right
            else: att_rect.right = self.hitbox.left
            att_rect.centery = self.hitbox.centery
            if att_rect.colliderect(target.hitbox) and target.hit_cooldown == 0:
                target.take_damage(10)
                target.hit_cooldown = 20

    def screen_wrap(self):
        if self.rect.centerx > SCREEN_WIDTH: self.rect.centerx = 0
        elif self.rect.centerx < 0: self.rect.centerx = SCREEN_WIDTH
    def face_target(self, target):
        if not self.is_dead and not self.is_attacking:
            if self.rect.centerx < target.rect.centerx:
                self.direction = 'right'
            else:
                self.direction = 'left'
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
            arrows_list.append(Arrow(sp_x, self.hitbox.centery, self.direction, self)) 
            self.arrow_shot = True

        # 4. Fizyka i Hitboxy (zawsze aktywne)
        self.apply_gravity()
        self.update_hitbox()
        self.check_attack_collision(target)
        
        if self.hit_cooldown > 0: 
            self.hit_cooldown -= 1
            
        # 5. Aktualizacja klatek animacji
        self.update_animation()
class Orc(Character):
    def __init__(self, x, y):
        super().__init__(x, y, "Assets/Orc")
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
        self.apply_gravity()
        self.update_hitbox()
        self.check_attack_collision(target)
        
        if self.hit_cooldown > 0: 
            self.hit_cooldown -= 1
            
        self.update_animation()
# Sterowanie
P1_CONTROLS = {'left': pygame.K_a, 'right': pygame.K_d, 'jump': pygame.K_w, 'atk1': pygame.K_r, 'atk2': pygame.K_t, 'special': pygame.K_y, 'block': pygame.K_u}
P2_CONTROLS = {'left': pygame.K_LEFT, 'right': pygame.K_RIGHT, 'jump': pygame.K_UP, 'atk1': pygame.K_m, 'atk2': pygame.K_COMMA, 'special': pygame.K_PERIOD, 'block': pygame.K_l}

async def main():
    global game_state, menu_index, p1_char_index, p2_char_index, game_mode
    global player1, player2 # Ważne, by mieć dostęp do globalnych graczy
    
    # Previews - tworzymy je raz przed pętlą
    p1_pre_soldier = Soldier(200, 150)
    p1_pre_orc = Orc(200, 150)
    p2_pre_soldier = Soldier(650, 150)
    p2_pre_orc = Orc(650, 150)
    
    # --- DODAJ TO: ---
    p1_pre_soldier.direction = 'right'
    p1_pre_orc.direction = 'right'
    p2_pre_soldier.direction = 'left'
    p2_pre_orc.direction = 'left'
    
    arrows = []
    run = True
    
    while run:
        screen.fill((30, 30, 30))
        events = pygame.event.get()
        
        for event in events:
            if event.type == pygame.QUIT:
                run = False
            
            if event.type == pygame.KEYDOWN:
                # --- NAWIGACJA MENU GŁÓWNE ---
                if game_state == STATE_MENU:
                    if event.key == pygame.K_UP:
                        menu_index = (menu_index - 1) % len(menu_options)
                    if event.key == pygame.K_DOWN:
                        menu_index = (menu_index + 1) % len(menu_options)
                    if event.key == pygame.K_RETURN:
                        if menu_index == 0: 
                            game_mode = "single"
                            game_state = STATE_CHAR_SELECT
                        elif menu_index == 1: 
                            game_mode = "multi"
                            game_state = STATE_CHAR_SELECT
                        elif menu_index == 2: 
                            run = False
                
                # --- NAWIGACJA WYBÓR POSTACI ---
                elif game_state == STATE_CHAR_SELECT:
                    if event.key == pygame.K_a: p1_char_index = (p1_char_index - 1) % 2
                    if event.key == pygame.K_d: p1_char_index = (p1_char_index + 1) % 2
                    if event.key == pygame.K_LEFT: p2_char_index = (p2_char_index - 1) % 2
                    if event.key == pygame.K_RIGHT: p2_char_index = (p2_char_index + 1) % 2
                    
                    if event.key == pygame.K_RETURN:
                        p1_n = available_chars[p1_char_index]
                        p2_n = available_chars[p2_char_index]
                        
                        player1 = Soldier(100, 250) if p1_n == "Soldier" else Orc(100, 250)
                        player2 = Soldier(700, 250) if p2_n == "Soldier" else Orc(700, 250)
                        player2.direction = 'left'
                        arrows = []
                        game_state = STATE_PLAYING
                
                # --- POWRÓT Z WALKI ---
                elif game_state == STATE_PLAYING:
                    if (player1.is_dead or player2.is_dead) and event.key == pygame.K_RETURN:
                        game_state = STATE_MENU

        # --- RENDEROWANIE (Poza pętlą eventów!) ---
        if game_state == STATE_MENU:
            title = font_main.render("FANTASY FIGHTER", True, (255, 215, 0))
            screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
            for i, opt in enumerate(menu_options):
                draw_keyboard_button(opt, 350, 180 + i*80, 300, 60, i == menu_index)

        elif game_state == STATE_CHAR_SELECT:
            label = font_sub.render("SELECT: [A/D] for P1, [Arrows] for P2, [ENTER] Start", True, (255, 255, 255))
            label_rect = label.get_rect(center=(SCREEN_WIDTH // 2, 50))
            screen.blit(label, label_rect)
            
            # Podgląd wybranej postaci
            p1_v = p1_pre_soldier if p1_char_index == 0 else p1_pre_orc
            p2_v = p2_pre_soldier if p2_char_index == 0 else p2_pre_orc
            
            p1_v.update_animation()
            p2_v.update_animation()
            
            screen.blit(p1_v.image, (200, 150))
            screen.blit(p2_v.image, (650, 150))
            
            # Podpisy pod postaciami
            p1_name = font_sub.render(f"P1: {available_chars[p1_char_index]}", True, (100, 100, 255))
            p2_name = font_sub.render(f"P2: {available_chars[p2_char_index]}", True, (255, 100, 100))
            screen.blit(p1_name, (220, 350))
            screen.blit(p2_name, (670, 350))

        elif game_state == STATE_PLAYING:
            player1.face_target(player2)
            player2.face_target(player1)
            
            player1.update(player2, arrows, P1_CONTROLS)
            player2.update(player1, arrows, P2_CONTROLS)
            player1.screen_wrap()
            player2.screen_wrap()
            
            for a in arrows[:]:
                a.update(player1, player2, arrows)
                screen.blit(a.image, a.rect)
            
            player1.draw_hp_bar(screen, 20, 20)
            player2.draw_hp_bar(screen, SCREEN_WIDTH - 20, 20, align_right=True)
            
            screen.blit(player1.image, player1.rect)
            screen.blit(player2.image, player2.rect)
            
            if player1.is_dead or player2.is_dead:
                win_text = "PLAYER 1 WINS!" if player2.is_dead else "PLAYER 2 WINS!"
                txt = font_main.render(win_text, True, (255, 255, 255))
                screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 200))
                sub = font_sub.render("Press ENTER for Menu", True, (200, 200, 200))
                screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, 280))

        pygame.display.flip()
        clock.tick(30)
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())
