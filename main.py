player1.face_target(player2)
            player2.face_target(player1)
            
            player1.update(player2, arrows, P1_CONTROLS)
            player2.update(player1, arrows, P2_CONTROLS)
