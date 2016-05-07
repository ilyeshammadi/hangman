"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from datetime import date, datetime
from protorpc import messages
from google.appengine.ext import ndb

# the point for each good responce when making a move
POINTS_PER_MOVE = 20


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    score = ndb.IntegerProperty(default=0)

    def calculate_ratio(self):
        number_games_played = len(Score.query(Score.user == self.key).fetch())
        number_games_won = len(Score.query(Score.user == self.key and Score.won == True).fetch())
        if number_games_played > 0:
            self.score = float(number_games_won) / float(number_games_played)
        self.put()

    def get_user_rank(self):
        users = User.query().order(User.score).fetch()
        return users.index(self) + 1

    def to_form(self):
        form = UserForm()
        form.name = self.name
        form.email = self.email
        form.total_played = len(Score.query(Score.user == self.key).fetch())
        form.won = len(Score.query(Score.user == self.key and Score.won == True).fetch())
        form.lost = len(Score.query(Score.user == self.key and Score.won == False).fetch())
        form.score = self.score
        form.ranking = self.get_user_rank()
        return form


class Move(ndb.Model):
    letter_played = ndb.StringProperty(required=True)
    is_correct = ndb.BooleanProperty(required=True)
    message = ndb.StringProperty(required=True)
    date = ndb.DateTimeProperty(required=True)

    @classmethod
    def new_move(cls, letter_played, is_correct, message):
        move = Move(letter_played=letter_played,
                    is_correct=is_correct,
                    message=message,
                    date=datetime.now())
        move.put()
        return move.key

    def to_form(self):
        form = MoveForm()
        form.letter_played = self.letter_played
        form.is_correct = self.is_correct
        form.message = self.message
        form.date = str(self.date)
        return form


class Game(ndb.Model):
    """Game object"""
    mystery_word = ndb.StringProperty(required=True)
    word_tryed = ndb.StringProperty()
    attempts_allowed = ndb.IntegerProperty(required=True, default=6)
    attempts_played = ndb.IntegerProperty(required=True, default=0)
    attempts_correct = ndb.IntegerProperty(required=True, default=0)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')
    score = ndb.IntegerProperty(default=0)
    message = ndb.StringProperty()
    moves_keys = ndb.KeyProperty(repeated=True, kind='Move')

    @classmethod
    def new_game(cls, user, word):
        """Creates and returns a new game"""
        game = Game(user=user, mystery_word=word)
        word = ''
        for i in game.mystery_word:
            word += '_'

        game.word_tryed = word
        game.put()
        return game
    def get_user(self):
        return User.query(User.key == self.user).get()

    def to_form(self):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.attempts_played = self.attempts_played
        form.attempts_correct = self.attempts_correct
        form.game_over = self.game_over
        form.mystery_word = self.mystery_word
        form.word_tryed = self.word_tryed
        form.message = self.message
        form.score = self.score
        form.moves = self.get_move_forms()
        return form

    def get_move_forms(self):
        moves = []
        for key in self.moves_keys:
            move = Move.query(Move.key == key).order(-Move.date).get()
            print move
            if move != None:
                moves.append(move)
        if len(moves) > 0:
            return MoveForms(items=[m.to_form() for m in moves])

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        if won:
            # add total score to the user score
            user = User.query(User.key == self.user).get()
            s = int(user.score)
            s += self.score
            user.score = s
            user.put()

            score = Score(user=self.user, date=date.today(), won=won, mystery_word=self.mystery_word,
                          score=self.score)
        else:
            score = Score(user=self.user, date=date.today(), won=won, mystery_word=self.mystery_word, score=0)
        # save the fame state
        score.put()

    def make_move(self, char):
        """ The game logic """
        word = list(self.word_tryed)
        m_word = list(self.mystery_word)

        print ''.join(word)
        print ''.join(m_word)

        self.attempts_played += 1

        if char in m_word and not char in word:
            for c in m_word:
                if c in char:
                    # get the index for the actual character
                    indices = [i for i, x in enumerate(m_word) if x == c]
                    for i in indices:
                        word[i] = c
            self.score += POINTS_PER_MOVE
            self.message = 'Nice work'
            self.moves_keys.append(Move.new_move(char, True, self.message))
            self.attempts_correct += 1
        else:
            self.message = 'Keep Going'
            self.moves_keys.append(Move.new_move(char, False, self.message))

        if self.attempts_played >= self.attempts_allowed:
            self.game_over = True
            self.message = 'Game Over'
            self.end_game(won=False)

        if word == m_word:
            self.game_over = True
            self.message = 'Well done you found it'
            self.end_game(won=True)

        self.word_tryed = ''.join(word)
        self.mystery_word = ''.join(m_word)

        self.put()

    def get_random_words(self):
        pass


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    score = ndb.IntegerProperty(required=True)
    mystery_word = ndb.StringProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), mystery_word=self.mystery_word, score=self.score)


class UserForm(messages.Message):
    name = messages.StringField(1, required=True)
    email = messages.StringField(2, required=True)
    total_played = messages.IntegerField(3, required=True)
    won = messages.IntegerField(4, required=True)
    lost = messages.IntegerField(5, required=True)
    score = messages.IntegerField(6)
    ranking = messages.IntegerField(7)


class MoveForm(messages.Message):
    letter_played = messages.StringField(1, required=True)
    is_correct = messages.BooleanField(2, required=True)
    message = messages.StringField(3, required=True)
    date = messages.StringField(4, required=True)


class MoveForms(messages.Message):
    items = messages.MessageField(MoveForm, 1, repeated=True)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1)
    attempts_played = messages.IntegerField(2)
    attempts_correct = messages.IntegerField(3)
    game_over = messages.BooleanField(4)
    user_name = messages.StringField(5)
    mystery_word = messages.StringField(6)
    word_tryed = messages.StringField(7)
    message = messages.StringField(8)
    score = messages.IntegerField(9)
    moves = messages.MessageField(MoveForms, 10)


class GameForms(messages.Message):
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    min = messages.IntegerField(2, default=1)
    max = messages.IntegerField(3, default=10)
    attempts = messages.IntegerField(4, default=5)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    guess = messages.IntegerField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    score = messages.IntegerField(4, required=True)
    mystery_word = messages.StringField(5, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
