import sys
import pygame

pygame.init()
pantalla = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Alcalde Digital - Test")

ejecutando = True
while ejecutando:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            ejecutando = False

    pantalla.fill((40, 44, 52))
    pygame.display.flip()

pygame.quit()
sys.exit()