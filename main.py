"""
Nigel Bazzeghin
CIT1203
Final Project - Rock, Paper, Scissors, Lizard, Spock

* Simple RPSLiSp game w/ mild "AI"
* QT UI
"""
import logging
import os
import pickle
import sys

from PyQt5 import QtGui
from PyQt5.QtCore import QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QApplication, QMainWindow
from numpy.random import choice
from qt_material import apply_stylesheet

from ui_MainWindow import Ui_MainWindow

logging.basicConfig(format='%(asctime)s - %(name)s - [%(levelname)s]: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def choice_to_value(playerChoice):
    value = ""
    if playerChoice == "r":
        value = "Rock"
    elif playerChoice == "p":
        value = "Paper"
    elif playerChoice == "s":
        value = "Scissors"
    elif playerChoice == "li":
        value = "Lizard"
    elif playerChoice == "sp":
        value = "Spock"
    else:
        value = "SUPER WIN"

    return value


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Fix so that image shows when run from python or bundled .exe
        path_to_logo = os.path.abspath(os.path.join(os.path.dirname(__file__), 'images/logo.png'))
        self.ui.logoImg.setPixmap(QtGui.QPixmap(path_to_logo))

        self.data = dict()

        # How long is each round in seconds
        self.roundTime = 3

        self.progressMaxValue = 1000000
        self.gameTimer = QTimer()

        # Ease the progress bar to give more tension to the player making a choice
        self.pbar_animation = QPropertyAnimation(self.ui.gameTime, b"value")
        self.pbar_animation.setEasingCurve(QEasingCurve.InCubic)
        self.pbar_animation.setDuration(self.roundTime * 1000)
        self.pbar_animation.setStartValue(self.progressMaxValue)
        self.pbar_animation.setEndValue(0)

        self.ui.gameTime.setMaximum(self.progressMaxValue)
        self.gameTimer.timeout.connect(self.handle_gameTime)
        self.ui.startGame.clicked.connect(lambda: self.start_game())
        self.ui.btnRock.clicked.connect(lambda: self.handle_choice("r"))
        self.ui.btnPaper.clicked.connect(lambda: self.handle_choice("p"))
        self.ui.btnScissors.clicked.connect(lambda: self.handle_choice("s"))
        self.ui.btnLizard.clicked.connect(lambda: self.handle_choice("li"))
        self.ui.btnSpock.clicked.connect(lambda: self.handle_choice("sp"))

        # What choice beats what other choices according to the rules
        self.rulesDict = {"r": ['s', 'li'], "p": ['r', 'sp'], "s": ['p', 'li'], "sp": ['r', 's'], "li": ['p', 'sp']}
        self.choices = ['r', 'p', 's', 'li', 'sp']

    def start_game(self):
        """
        Starts game and creates/loads save file that contains the player's name, win/losses, and
        historical probability for "AI" choices.
        :return:
        """
        if self.ui.playerName.text() != "":
            self.ui.statusbar.showMessage("Good Luck!", 3000)
            self.ui.widgetStack.setCurrentIndex(1)

            self.gameTimer.start(self.roundTime * 1000)
            self.ui.playerLabel.setText(f"<h1>{self.ui.playerName.text()}</h2>")

            self.pbar_animation.start()

            playerName = self.ui.playerName.text().lower()
            filename = playerName + ".dat"

            if os.path.exists(filename):
                infile = open(filename, 'rb')
                logger.info(f"OPEN DAT:{filename}")
                self.data = pickle.load(infile)
                infile.close()
            else:
                outfile = open(filename, 'wb')
                self.data = {
                    "player": playerName,
                    "wins": 0,
                    "losses": 0,
                    "probability": [0.2, 0.2, 0.2, 0.2, 0.2]
                }
                pickle.dump(self.data, outfile)
                outfile.close()

            self.update_data()
            self.gameMessage('<b>Welcome to RPSLiSp!!!</b>')
            self.gameMessage('Time is ticking, choose your option!')
            self.gameMessage('========================================')

            logger.info("START GAME")
        else:
            self.ui.statusbar.showMessage("Your name is required!", 3000)
            logger.info("NAMED REQUIRED")

    def handle_gameTime(self):
        """
        Timer handler that awards the computer a point if the player doesnt act in time.
        :return:
        """
        self.gameMessage(" ")
        self.gameMessage('<b style="color:red">TIME UP!</b> Next round!')
        self.gameMessage("<b style='color:#E76F51'>===== COMPUTER WINS BY DEFAULT =====</b>")
        self.data["losses"] += 1
        self.update_data()
        self.pbar_animation.stop()
        self.pbar_animation.start()

    def reset_timer(self):
        self.gameTimer.stop()
        self.pbar_animation.stop()
        self.gameTimer.start(self.roundTime * 1000)
        self.pbar_animation.start()

    def handle_choice(self, playerChoice):
        value = choice_to_value(playerChoice)
        self.ui.statusbar.showMessage(f"{value}!", 3000)
        self.check_winner(playerChoice)

    def check_winner(self, playerChoice):
        computer_choice = choice(self.choices, 1, p=self.data["probability"])
        self.gameMessage(" ")
        self.gameMessage(
            f"{self.ui.playerName.text()}: <b style='color:#E9C46A'>{choice_to_value(playerChoice)}</b> vs "
            f"COMPUTER: <b style='color:#E9C46A'>{choice_to_value(computer_choice[0])}</b> ")

        if computer_choice[0] == playerChoice:
            self.gameMessage("<b style='color:#264653'>===== TIE! =====</b>")
        elif computer_choice[0] in self.rulesDict[playerChoice]:
            self.gameMessage("<b style='color:#2A9D8F'>===== PLAYER WINS =====</b>")
            self.data["wins"] += 1
            self.update_probability(playerChoice)
        else:
            self.gameMessage("<b style='color:#E76F51'>===== COMPUTER WINS =====</b>")
            self.data["losses"] += 1

        self.reset_timer()
        self.update_data()

    def update_probability(self, playerChoice):
        """
        The "AI" takes the choice the player made and increases the probability that it will pick
        a choice to beat the player next time as well as decrease the probability that it will pick
        a choice that would allow the player to beat it. Probability is fed into numpy.choice() for
        "random" selection.
        :param playerChoice:
        :return:
        """
        choiceIndex = {"r": 0, "p": 1, "s": 2, "li": 3, "sp": 4}
        oppositeRules = {"r": ['p', 'sp'], "p": ['s', 'li'], "s": ['r', 'sp'], "sp": ['p', 'li'], "li": ['s', 'r']}

        newProbabilityArray = self.data["probability"]

        for rule in oppositeRules[playerChoice]:
            logger.info(f"Increase rule: {rule} ")
            newProb = format(newProbabilityArray[choiceIndex[rule]] + 0.02, '.2f')
            if float(newProb) <= 0.98:
                newProbabilityArray[choiceIndex[rule]] = float(newProb)

        for rule in self.rulesDict[playerChoice]:
            logger.info(f"Decrease rule: {rule} ")
            newProb = format(newProbabilityArray[choiceIndex[rule]] - 0.02, '.2f')
            if float(newProb) >= 0.02:
                newProbabilityArray[choiceIndex[rule]] = float(newProb)

        # To prevent crash reset array when it gets out of bounds for numpy.choice()
        if sum(newProbabilityArray) > 1.0:
            newProbabilityArray = [0.2, 0.2, 0.2, 0.2, 0.2]

        logger.info(sum(newProbabilityArray))
        self.data["probability"] = newProbabilityArray
        logger.info(self.data["probability"])

    def gameMessage(self, message):
        self.ui.gameLog.append(message)

    def update_data(self):
        """
        Updates UI for player wins and losses
        :return:
        """
        self.ui.playerScore.display(self.data["wins"])
        self.ui.computerScore.display(self.data["losses"])

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handle clean up after application is closed
        :param event:
        :return:
        """
        self.gameTimer.stop()
        if self.ui.playerName.text() != "":
            filename = self.data["player"] + ".dat"
            outfile = open(filename, 'wb')
            pickle.dump(self.data, outfile)
            outfile.close()
            logger.info(f"CLOSING: {filename}")


def main():
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_teal.xml')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
