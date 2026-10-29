import pygame
import math
import random
import requests

# --- КОНСТАНТЫ ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (100, 100, 100)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (255, 0, 255)
ORANGE = (255, 165, 0)
BROWN = (139, 69, 19)
CYAN = (0, 255, 255)
PINK = (255, 105, 180)

# Параметры поля боя
BOX_X = 200
BOX_Y = 300
BOX_WIDTH = 400
BOX_HEIGHT = 200

# --- КЛАССЫ ---

class Particle(pygame.sprite.Sprite):
    """Класс для эффектов взрыва"""
    def __init__(self, x, y, color):
        super().__init__()
        self.color = color
        self.size = random.randint(2, 5)
        self.image = pygame.Surface((self.size, self.size))
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 3)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 30 # Время жизни частицы

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.kill()

class PowerUp(pygame.sprite.Sprite):
    """Бонусы, выпадающие из врагов"""
    def __init__(self, x, y, p_type):
        super().__init__()
        self.p_type = p_type # 'heal', 'shield', 'speed'
        self.size = 15
        self.image = pygame.Surface((self.size, self.size))
        
        if p_type == 'heal':
            self.image.fill(GREEN)
        elif p_type == 'shield':
            self.image.fill(BLUE)
        elif p_type == 'speed':
            self.image.fill(YELLOW)
            
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        self.vy = 1 # Медленно падает вниз
        self.life = 300 # Исчезает через 5 секунд

    def update(self):
        self.rect.y += self.vy
        self.life -= 1
        if self.life <= 0 or self.rect.top > SCREEN_HEIGHT:
            self.kill()

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.size = 10
        self.image = pygame.Surface((self.size, self.size))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        
        self.rect.centerx = BOX_X + BOX_WIDTH // 2
        self.rect.centery = BOX_Y + BOX_HEIGHT // 2
        
        self.base_speed = 4
        self.speed = self.base_speed
        self.hp = 10
        self.max_hp = 10
        self.invincible_timer = 0
        self.shield_active = False
        self.shield_timer = 0

    def update(self):
        keys = pygame.key.get_pressed()
        current_speed = self.speed
        
        # Ускорение если активен бонус скорости
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
             current_speed *= 0.6 # Замедление для точности при зажатом шифте, или можно сделать ускорение

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= current_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += current_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.rect.y -= current_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.rect.y += current_speed
            
        # Границы поля
        half_size = self.size // 2
        if self.rect.left < BOX_X + half_size:
            self.rect.left = BOX_X + half_size
        if self.rect.right > BOX_X + BOX_WIDTH - half_size:
            self.rect.right = BOX_X + BOX_WIDTH - half_size
        if self.rect.top < BOX_Y + half_size:
            self.rect.top = BOX_Y + half_size
        if self.rect.bottom > BOX_Y + BOX_HEIGHT - half_size:
            self.rect.bottom = BOX_Y + BOX_HEIGHT - half_size
            
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            
        if self.shield_timer > 0:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield_active = False
                self.speed = self.base_speed

    def apply_powerup(self, p_type):
        if p_type == 'heal':
            self.hp = min(self.hp + 2, self.max_hp)
        elif p_type == 'shield':
            self.shield_active = True
            self.shield_timer = 300 # 5 секунд
        elif p_type == 'speed':
            self.speed = self.base_speed * 1.5
            self.shield_timer = 300 # Используем тот же таймер для длительности эффекта

    def draw_heart(self, surface):
        if self.invincible_timer > 0 and self.invincible_timer % 10 < 5:
            return
        
        # Рисуем игрока
        pygame.draw.rect(surface, RED, self.rect)
        
        # Если активен щит, рисуем ауру
        if self.shield_active:
            pygame.draw.circle(surface, BLUE, self.rect.center, self.size + 5, 2)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, homing=False):
        super().__init__()
        self.width = 8
        self.height = 8
        self.image = pygame.Surface((self.width, self.height))
        if homing:
            self.image.fill(CYAN)
            self.homing = True
            self.homing_strength = 0.05
        else:
            self.image.fill(WHITE)
            self.homing = False
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        self.vx = vx
        self.vy = vy
        self.lifetime = 0

    def update(self, player_rect=None):
        if hasattr(self, 'homing') and self.homing and player_rect and self.lifetime < 60:
            dx = player_rect.centerx - self.rect.centerx
            dy = player_rect.centery - self.rect.centery
            distance = math.sqrt(dx*dx + dy*dy)
            if distance > 0:
                target_vx = (dx / distance) * 3
                target_vy = (dy / distance) * 3
                self.vx += (target_vx - self.vx) * self.homing_strength
                self.vy += (target_vy - self.vy) * self.homing_strength
                
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.lifetime += 1
        
        if (self.rect.y > SCREEN_HEIGHT + 50 or self.rect.y < -50 or
            self.rect.x > SCREEN_WIDTH + 50 or self.rect.x < -50):
            self.kill()

class LaserBeam(pygame.sprite.Sprite):
    def __init__(self, side, duration=30):
        super().__init__()
        self.side = side
        self.duration = duration
        self.timer = 0
        half_width = SCREEN_WIDTH // 2
        self.image = pygame.Surface((half_width, SCREEN_HEIGHT))
        self.image.fill(YELLOW)
        self.image.set_alpha(180)
        self.rect = self.image.get_rect()
        if side == 'left':
            self.rect.x = 0
        else:
            self.rect.x = half_width
        self.rect.y = 0
        self.damage = 5

    def update(self):
        self.timer += 1
        if self.timer >= self.duration:
            self.kill()

class WarningSign(pygame.sprite.Sprite):
    def __init__(self, side, duration=120):
        super().__init__()
        self.side = side
        self.duration = duration
        self.timer = 0
        sign_size = 80
        self.image = pygame.Surface((sign_size, sign_size))
        self.image.fill(RED)
        font = pygame.font.SysFont("Arial", 60, bold=True)
        exclamation = font.render("!", True, WHITE)
        exclamation_rect = exclamation.get_rect(center=(sign_size // 2, sign_size // 2))
        self.image.blit(exclamation, exclamation_rect)
        self.rect = self.image.get_rect()
        half_width = SCREEN_WIDTH // 2
        if side == 'left':
            self.rect.centerx = half_width // 2
        else:
            self.rect.centerx = half_width + half_width // 2
        self.rect.centery = SCREEN_HEIGHT // 2

    def update(self):
        self.timer += 1
        if self.timer % 10 < 5:
            self.image.set_alpha(255)
        else:
            self.image.set_alpha(100)
        if self.timer >= self.duration:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type):
        super().__init__()
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        self.hp = 3
        self.size = 50
        self.image = pygame.Surface((self.size, self.size))
        
        # Настройка параметров в зависимости от типа
        if enemy_type == "shooter":
            self.color = BLUE
            self.hp = 3
        elif enemy_type == "spreader":
            self.color = GREEN
            self.hp = 4
        elif enemy_type == "wave":
            self.color = PURPLE
            self.hp = 3
        elif enemy_type == "spiral":
            self.color = ORANGE
            self.hp = 4
        elif enemy_type == "bomber":
            self.color = BROWN
            self.hp = 5
        elif enemy_type == "homing":
            self.color = CYAN
            self.hp = 3
        elif enemy_type == "laser":
            self.color = YELLOW
            self.hp = 6
        elif enemy_type == "dasher": # Новый тип: рывок
            self.color = PINK
            self.hp = 2
            self.size = 40
        elif enemy_type == "tank": # Новый тип: танк
            self.color = GRAY
            self.hp = 15
            self.size = 70
        else:
            self.color = GRAY
            
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        
        self.attack_timer = 0
        self.attack_duration = 180
        self.spiral_angle = 0
        
        # Для лазерного врага
        self.laser_phase = 1
        self.laser_side = 'left'
        self.laser_warning_timer = 0
        
        # Для дэшера
        self.dash_timer = 0
        self.is_dashing = False
        self.dash_target_x = x
        self.dash_target_y = y

    def update(self, bullets_group, player_rect, laser_beams_group, warning_signs_group):
        self.attack_timer += 1
        
        # Логика движения для новых типов
        if self.enemy_type == "dasher":
            self.dasher_movement(player_rect)
            
        if self.enemy_type == "shooter":
            self.shooter_pattern(bullets_group, player_rect)
        elif self.enemy_type == "spreader":
            self.spreader_pattern(bullets_group, player_rect)
        elif self.enemy_type == "wave":
            self.wave_pattern(bullets_group, player_rect)
        elif self.enemy_type == "spiral":
            self.spiral_pattern(bullets_group, player_rect)
        elif self.enemy_type == "bomber":
            self.bomber_pattern(bullets_group, player_rect)
        elif self.enemy_type == "homing":
            self.homing_pattern(bullets_group, player_rect)
        elif self.enemy_type == "laser":
            self.laser_pattern(bullets_group, player_rect, laser_beams_group, warning_signs_group)
        elif self.enemy_type == "dasher":
            self.dasher_pattern(bullets_group, player_rect)
        elif self.enemy_type == "tank":
            self.tank_pattern(bullets_group, player_rect)
            
        # Пассивное снижение HP (механика выживания)
        if self.attack_timer > self.attack_duration:
            self.hp -= 0.02
            
        return self.hp > 0

    def dasher_movement(self, player_rect):
        if not self.is_dashing:
            self.dash_timer += 1
            if self.dash_timer > 120: # Подготовка к рывку каждые 2 секунды
                self.is_dashing = True
                self.dash_timer = 0
                # Выбираем точку для рывка (немного мимо игрока или в него)
                self.dash_target_x = player_rect.centerx
                self.dash_target_y = player_rect.centery
        else:
            # Быстрое движение к цели
            dx = self.dash_target_x - self.rect.centerx
            dy = self.dash_target_y - self.rect.centery
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 5:
                self.rect.x += (dx/dist) * 8
                self.rect.y += (dy/dist) * 8
            else:
                self.is_dashing = False
                self.dash_timer = 0

    def shooter_pattern(self, bullets_group, player_rect):
        if self.attack_timer % 30 == 0:
            dx = player_rect.centerx - self.rect.centerx
            dy = player_rect.centery - self.rect.centery
            distance = math.sqrt(dx*dx + dy*dy)
            if distance > 0:
                speed = 4
                vx = (dx / distance) * speed
                vy = (dy / distance) * speed
                bullet = Bullet(self.rect.centerx, self.rect.centery, vx, vy)
                bullets_group.add(bullet)

    def spreader_pattern(self, bullets_group, player_rect):
        if self.attack_timer % 45 == 0:
            base_angle = math.atan2(
                player_rect.centery - self.rect.centery,
                player_rect.centerx - self.rect.centerx
            )
            for i in range(5):
                angle_offset = (i - 2) * 0.3
                angle = base_angle + angle_offset
                speed = 3.5
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                bullet = Bullet(self.rect.centerx, self.rect.centery, vx, vy)
                bullets_group.add(bullet)

    def wave_pattern(self, bullets_group, player_rect):
        if self.attack_timer % 20 == 0:
            if self.rect.centery < SCREEN_HEIGHT // 2:
                vy = 3
            else:
                vy = -3
            vx = math.sin(self.attack_timer * 0.1) * 2
            bullet = Bullet(self.rect.centerx, self.rect.centery, vx, vy)
            bullets_group.add(bullet)

    def spiral_pattern(self, bullets_group, player_rect):
        if self.attack_timer % 8 == 0:
            self.spiral_angle += 0.3
            speed = 3
            vx = math.cos(self.spiral_angle) * speed
            vy = math.sin(self.spiral_angle) * speed
            bullet = Bullet(self.rect.centerx, self.rect.centery, vx, vy)
            bullets_group.add(bullet)

    def bomber_pattern(self, bullets_group, player_rect):
        if self.attack_timer % 60 == 0:
            num_bullets = 12
            for i in range(num_bullets):
                angle = (i / num_bullets) * 2 * math.pi
                speed = 2.5
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                bullet = Bullet(self.rect.centerx, self.rect.centery, vx, vy)
                bullets_group.add(bullet)

    def homing_pattern(self, bullets_group, player_rect):
        if self.attack_timer % 50 == 0:
            dx = player_rect.centerx - self.rect.centerx
            dy = player_rect.centery - self.rect.centery
            distance = math.sqrt(dx*dx + dy*dy)
            if distance > 0:
                speed = 2
                vx = (dx / distance) * speed
                vy = (dy / distance) * speed
                bullet = Bullet(self.rect.centerx, self.rect.centery, vx, vy, homing=True)
                bullets_group.add(bullet)

    def laser_pattern(self, bullets_group, player_rect, laser_beams_group, warning_signs_group):
        if self.laser_phase == 1:
            self.laser_warning_timer += 1
            if self.laser_warning_timer == 1:
                warning = WarningSign(self.laser_side, duration=120)
                warning_signs_group.add(warning)
            if self.laser_warning_timer >= 120:
                self.laser_phase = 2
                laser = LaserBeam(self.laser_side, duration=30)
                laser_beams_group.add(laser)
        if self.laser_phase == 2:
            self.laser_warning_timer += 1
            if self.laser_warning_timer >= 150:
                self.laser_phase = 1
                self.laser_warning_timer = 0
                self.laser_side = 'right' if self.laser_side == 'left' else 'left'

    def dasher_pattern(self, bullets_group, player_rect):
        # Стреляет короткими очередями во время рывка
        if self.is_dashing and self.attack_timer % 5 == 0:
             dx = player_rect.centerx - self.rect.centerx
             dy = player_rect.centery - self.rect.centery
             distance = math.sqrt(dx*dx + dy*dy)
             if distance > 0:
                 speed = 6
                 vx = (dx / distance) * speed
                 vy = (dy / distance) * speed
                 bullet = Bullet(self.rect.centerx, self.rect.centery, vx, vy)
                 bullets_group.add(bullet)

    def tank_pattern(self, bullets_group, player_rect):
        # Медленно стреляет веером
        if self.attack_timer % 90 == 0:
            base_angle = math.atan2(
                player_rect.centery - self.rect.centery,
                player_rect.centerx - self.rect.centerx
            )
            for i in range(3):
                angle_offset = (i - 1) * 0.5
                angle = base_angle + angle_offset
                speed = 2
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                bullet = Bullet(self.rect.centerx, self.rect.centery, vx, vy)
                bullets_group.add(bullet)

class BattleBox:
    def __init__(self):
        self.x = BOX_X
        self.y = BOX_Y
        self.w = BOX_WIDTH
        self.h = BOX_HEIGHT

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, (self.x, self.y, self.w, self.h), 4)

class WaveManager:
    def __init__(self):
        self.enemies = []
        self.current_wave = 0
        self.waves = self.create_waves()
        self.spawn_timer = 0
        self.spawn_delay = 60

    def create_waves(self):
        waves = []
        # Волна 1: Один стрелок
        waves.append([{"type": "shooter", "x": SCREEN_WIDTH // 2, "y": 100}])
        # Волна 2: Два стрелка
        waves.append([
            {"type": "shooter", "x": 250, "y": 100},
            {"type": "shooter", "x": 550, "y": 100}
        ])
        # Волна 3: Разбрасыватель
        waves.append([{"type": "spreader", "x": SCREEN_WIDTH // 2, "y": 100}])
        # Волна 4: Комбо
        waves.append([
            {"type": "shooter", "x": 200, "y": 100},
            {"type": "spreader", "x": 600, "y": 100}
        ])
        # Волна 5: Волновой стрелок
        waves.append([{"type": "wave", "x": SCREEN_WIDTH // 2, "y": 100}])
        # Волна 6: Финальная - все типы
        waves.append([
            {"type": "shooter", "x": 150, "y": 100},
            {"type": "spreader", "x": 400, "y": 100},
            {"type": "wave", "x": 650, "y": 100}
        ])
        # Волна 7: Спиральный враг
        waves.append([{"type": "spiral", "x": SCREEN_WIDTH // 2, "y": 100}])
        # Волна 8: Бомбер + стрелок
        waves.append([
            {"type": "bomber", "x": 300, "y": 100},
            {"type": "shooter", "x": 500, "y": 100}
        ])
        # Волна 9: Самонаводящиеся + лазер
        waves.append([
            {"type": "homing", "x": 250, "y": 100},
            {"type": "laser", "x": 550, "y": 100}
        ])
        # Волна 10: НОВЫЕ ВРАГИ - Дэшер и Танк
        waves.append([
            {"type": "dasher", "x": 200, "y": 100},
            {"type": "tank", "x": 600, "y": 100}
        ])
        # Волна 11: Финальная битва
        waves.append([
            {"type": "spiral", "x": 150, "y": 100},
            {"type": "bomber", "x": 400, "y": 100},
            {"type": "laser", "x": 650, "y": 100},
            {"type": "dasher", "x": 300, "y": 150}
        ])
        return waves

    def update(self, bullets_group, player_rect, enemies_group, laser_beams_group, warning_signs_group, particles_group, powerups_group):
        if len(self.enemies) == 0:
            self.spawn_timer += 1
            if self.spawn_timer >= self.spawn_delay:
                if self.current_wave < len(self.waves):
                    self.spawn_wave(enemies_group)
                    self.spawn_timer = 0
                else:
                    return False
        
        # Проверка смерти врагов и создание эффектов
        for enemy in self.enemies[:]:
            is_alive = enemy.update(bullets_group, player_rect, laser_beams_group, warning_signs_group)
            if not is_alive:
                # Создаем взрыв
                for _ in range(10):
                    particles_group.add(Particle(enemy.rect.centerx, enemy.rect.centery, enemy.color))
                
                # Шанс выпадения бонуса (20%)
                if random.random() < 0.2:
                    p_type = random.choice(['heal', 'shield', 'speed'])
                    powerups_group.add(PowerUp(enemy.rect.centerx, enemy.rect.centery, p_type))
                    
                self.enemies.remove(enemy)
                enemies_group.remove(enemy)
        return True

    def spawn_wave(self, enemies_group):
        wave_data = self.waves[self.current_wave]
        for enemy_data in wave_data:
            enemy = Enemy(
                enemy_data["x"],
                enemy_data["y"],
                enemy_data["type"]
            )
            self.enemies.append(enemy)
            enemies_group.add(enemy)
        self.current_wave += 1
        print(f"Волна {self.current_wave} началась!")

# --- ФУНКЦИЯ ОТПРАВКИ РЕЗУЛЬТАТА НА СЕРВЕР ---
def send_score_to_server(player_name, max_wave, score):
    try:
        url = 'http://localhost:5000/api/submit_score'
        data = {
            'player_name': player_name,
            'max_wave': max_wave,
            'score': score
        }
        response = requests.post(url, json=data, timeout=3)
        if response.status_code == 201:
            print("✅ Результат отправлен на сервер!")
            return True
        else:
            print("❌ Ошибка отправки результата")
            return False
    except Exception as e:
        print(f"❌ Не удалось подключиться к серверу: {e}")
        return False

# --- ОСНОВНОЙ ЦИКЛ ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Bullet Hell: Enhanced")
    clock = pygame.time.Clock()
    
    player = Player()
    battle_box = BattleBox()
    wave_manager = WaveManager()
    
    all_sprites = pygame.sprite.Group()
    enemies_group = pygame.sprite.Group()
    bullets_group = pygame.sprite.Group()
    laser_beams_group = pygame.sprite.Group()
    warning_signs_group = pygame.sprite.Group()
    particles_group = pygame.sprite.Group()
    powerups_group = pygame.sprite.Group()
    
    all_sprites.add(player)
    
    running = True
    game_over = False
    player_name = ""
    score_submitted = False
    show_input = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if game_over and show_input and not score_submitted:
                    if event.key == pygame.K_RETURN and len(player_name) > 0:
                        if player.hp <= 0:
                            final_wave = wave_manager.current_wave - 1
                        else:
                            final_wave = wave_manager.current_wave
                        score = final_wave * 100 + player.hp * 50
                        if send_score_to_server(player_name, final_wave, score):
                            score_submitted = True
                            show_input = False
                    elif event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                    elif len(player_name) < 15:
                        if event.unicode.isprintable():
                            player_name += event.unicode
        
        if not game_over:
            player.update()
            game_continues = wave_manager.update(
                bullets_group, player.rect, enemies_group, 
                laser_beams_group, warning_signs_group, 
                particles_group, powerups_group
            )
            
            if not game_continues:
                print("ПОБЕДА! Все волны пройдены!")
                game_over = True
                
            bullets_group.update(player.rect)
            laser_beams_group.update()
            warning_signs_group.update()
            particles_group.update()
            powerups_group.update()
            
            # Сбор бонусов
            collected_powerups = pygame.sprite.spritecollide(player, powerups_group, True)
            for pu in collected_powerups:
                player.apply_powerup(pu.p_type)
                print(f"Подобран бонус: {pu.p_type}")

            # Столкновения с пулями
            if player.invincible_timer <= 0 and not player.shield_active:
                hits = pygame.sprite.spritecollide(player, bullets_group, True)
                if hits:
                    player.hp -= 1
                    player.invincible_timer = 60
                    print(f"Урон! HP: {player.hp}")
                    if player.hp <= 0:
                        print("GAME OVER")
                        game_over = True
                        
                        
    """Класс для предупреждающего знака на всю половину экрана"""
    def __init__(self, side, duration=120):
        super().__init__()
        self.side = side
        self.duration = duration
        self.timer = 0
        
        # Размер - половина экрана
        half_width = SCREEN_WIDTH // 2
        self.image = pygame.Surface((half_width, SCREEN_HEIGHT))
        
        # Полупрозрачный красный фон
        self.image.fill(RED)
        self.image.set_alpha(100)
        
        # Большой восклицательный знак по центру
        font = pygame.font.SysFont("Arial", 300, bold=True)
        exclamation = font.render("!", True, WHITE)
        exclamation.set_alpha(200)
        exclamation_rect = exclamation.get_rect(center=(half_width // 2, SCREEN_HEIGHT // 2))
        self.image.blit(exclamation, exclamation_rect)
        
        self.rect = self.image.get_rect()
        
        # Позиционируем на соответствующей половине
        if side == 'left':
            self.rect.x = 0
        else:
            self.rect.x = half_width
        self.rect.y = 0

    def update(self):
        self.timer += 1
        # Мигание всей половины
        if self.timer % 10 < 5:
            self.image.set_alpha(150)
        else:
            self.image.set_alpha(50)
        
        if self.timer >= self.duration:
            self.kill()
            # Столкновения с лазером
            if player.invincible_timer <= 0 and not player.shield_active:
                laser_hits = pygame.sprite.spritecollide(player, laser_beams_group, False)
                if laser_hits:
                    player.hp -= 5
                    player.invincible_timer = 60
                    print(f"ЛАЗЕР! Урон 5 HP! HP: {player.hp}")
                    if player.hp <= 0:
                        print("GAME OVER")
                        game_over = True

        # --- ОТРИСОВКА ---
        screen.fill(BLACK)
        battle_box.draw(screen)
        
        enemies_group.draw(screen)
        bullets_group.draw(screen)
        warning_signs_group.draw(screen)
        laser_beams_group.draw(screen)
        powerups_group.draw(screen)
        particles_group.draw(screen)
        
        if not game_over:
            player.draw_heart(screen)
            
        # Интерфейс
        font = pygame.font.SysFont("Arial", 24)
        
        # Полоска здоровья
        hp_ratio = player.hp / player.max_hp
        bar_width = 200
        pygame.draw.rect(screen, RED, (BOX_X, BOX_Y + BOX_HEIGHT + 20, bar_width, 20))
        pygame.draw.rect(screen, GREEN, (BOX_X, BOX_Y + BOX_HEIGHT + 20, bar_width * hp_ratio, 20))
        pygame.draw.rect(screen, WHITE, (BOX_X, BOX_Y + BOX_HEIGHT + 20, bar_width, 20), 2)
        
        hp_text = font.render(f"HP: {player.hp}/{player.max_hp}", True, WHITE)
        screen.blit(hp_text, (BOX_X + bar_width + 10, BOX_Y + BOX_HEIGHT + 20))
        
        wave_text = font.render(f"Волна: {wave_manager.current_wave}/{len(wave_manager.waves)}", True, WHITE)
        screen.blit(wave_text, (BOX_X + 200, BOX_Y + BOX_HEIGHT + 50))
        
        if player.shield_active:
            shield_text = font.render("ЩИТ АКТИВЕН!", True, BLUE)
            screen.blit(shield_text, (SCREEN_WIDTH // 2 - 50, 20))

        if game_over:
            if player.hp <= 0:
                game_over_text = font.render("GAME OVER", True, RED)
                final_wave = wave_manager.current_wave - 1
            else:
                game_over_text = font.render("ПОБЕДА!", True, GREEN)
                final_wave = wave_manager.current_wave
                
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60))
            screen.blit(game_over_text, text_rect)
            
            wave_info = font.render(f"Достигнута волна: {final_wave}", True, WHITE)
            wave_rect = wave_info.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
            screen.blit(wave_info, wave_rect)
            
            if show_input and not score_submitted:
                prompt = font.render("Введите имя и нажмите Enter:", True, YELLOW)
                prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
                screen.blit(prompt, prompt_rect)
                
                cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
                name_display = player_name + cursor
                name_text = font.render(name_display, True, WHITE)
                name_rect = name_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
                screen.blit(name_text, name_rect)
                
            elif score_submitted:
                success_text = font.render("Результат сохранён!", True, GREEN)
                success_rect = success_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
                screen.blit(success_text, success_rect)
                
                restart_text = font.render("Нажмите R для новой игры", True, GRAY)
                restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
                screen.blit(restart_text, restart_rect)
                
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                return main()
                
        pygame.display.flip()
        clock.tick(FPS)
        
    pygame.quit()

if __name__ == "__main__":
    main()