import random
import math
from gametext import appearance_outcomes, base_string

class Weather:
    def __init__(self, game):
        self.name = "Sunny"
        self.emoji = "🌞"

    def __str__(self):
        return f"{self.emoji} {self.name}"

    def modify_atbat_stats(self, player_rolls):
        # Activates before batting
        pass

    def modify_steal_stats(self, roll):
        pass

    def modify_atbat_roll(self, outcome, roll, defender):
        # activates after batter roll
        pass

    def activate(self, game, result):
        # activates after the batter calculation. modify result, or just return another thing
        pass

    def on_choose_next_batter(self, game):
        pass

    def on_flip_inning(self, game):
        pass

    def modify_top_of_inning_message(self, game, state):
        pass

    def modify_atbat_message(self, game, state):
        pass


class Supernova(Weather):
    def __init__(self, game):
        self.name = "Supernova"
        self.emoji = "🌟"

    def modify_atbat_stats(self, roll):
        roll["pitch_stat"] *= 0.9

class Midnight(Weather):
    def __init__(self, game):
        self.name = "Midnight"
        self.emoji = "🕶"

    def modify_steal_stats(self, roll):
        roll["run_stars"] *= 2

class SlightTailwind(Weather):
    def __init__(self, game):
        self.name = "Slight Tailwind"
        self.emoji = "🏌️‍♀️"

    def activate(self, game, result):
        if game.top_of_inning:
            offense_team = game.teams["away"]
            defense_team = game.teams["home"]
        else:
            offense_team = game.teams["home"]
            defense_team = game.teams["away"]

        if "mulligan" not in game.last_update[0].keys() and not result["ishit"] and result["text"] != appearance_outcomes.walk: 
            mulligan_roll_target = -((((game.get_batter().stlats["batting_stars"])-5)/6)**2)+1
            if random.random() > mulligan_roll_target and game.get_batter().stlats["batting_stars"] <= 5:
                result.clear()
                result.update({
                    "text": f"{game.get_batter()} would have gone out, but they took a mulligan!",
                    "text_only": True,
                    "weather_message": True,
                })

class HeavySnow(Weather):
    def __init__(self, game):
        self.name = "Heavy Snow"
        self.emoji = "❄"
        self.counter_away = random.randint(0,len(game.teams['away'].lineup)-1)
        self.counter_home = random.randint(0,len(game.teams['home'].lineup)-1)

        self.swapped_batter_data = None

    def activate(self, game, result):        
        if self.swapped_batter_data:
            original, sub = self.swapped_batter_data
            self.swapped_batter_data = None
            result.clear()
            result.update({
                "snow_atbat": True,
                "text": f"{original.name}'s hands are too cold! {sub.name} is forced to bat!",
                "text_only": True,
                "weather_message": True,
            })

    def on_flip_inning(self, game):
        if game.top_of_inning and self.counter_away < game.teams["away"].lineup_position:
            self.counter_away = self.pitcher_insert_index(game.teams["away"])

        if not game.top_of_inning and self.counter_home < game.teams["home"].lineup_position:
            self.counter_home = self.pitcher_insert_index(game.teams["home"])

    def pitcher_insert_index(self, this_team):
        rounds = math.ceil(this_team.lineup_position / len(this_team.lineup))
        position = random.randint(0, len(this_team.lineup)-1)
        return rounds * len(this_team.lineup) + position

    def on_choose_next_batter(self, game):
        if game.top_of_inning:
            bat_team = game.teams["away"]
            counter = self.counter_away
        else:
            bat_team = game.teams["home"]
            counter = self.counter_home

        if bat_team.lineup_position == counter:
            self.swapped_batter_data = (game.current_batter, bat_team.pitcher) # store this to generate the message during activate()
            game.current_batter = bat_team.pitcher

class Twilight(Weather):
    def __init__(self,game):
        self.name = "Twilight"
        self.emoji = "👻"

    def modify_atbat_roll(self, outcome, roll, defender):
        error_line = - (math.log(defender.stlats["defense_stars"] + 1)/50) + 1
        error_roll = random.random()
        if error_roll > error_line:
            outcome["error"] = True
            outcome["weather_message"] = True
            outcome["defender"] = defender
            roll["pb_system_stat"] = 0.1

    def modify_atbat_message(self, this_game, state):
        result = this_game.last_update[0]
        if "error" in result.keys():
            state["update_text"] = f"{result['batter']}'s hit goes ethereal, and {result['defender']} can't catch it! {result['batter']} reaches base safely."
            if this_game.last_update[1] > 0:
                state["update_text"] += f" {this_game.last_update[1]} runs scored!"

class ThinnedVeil(Weather):
    def __init__(self,game):
        self.name = "Thinned Veil"
        self.emoji = "🌌"

    def activate(self, game, result):
        if result["ishit"]:
           if result["text"] == appearance_outcomes.homerun or result["text"] == appearance_outcomes.grandslam:
                result["veil"] = True

    def modify_atbat_message(self, game, state):
        if "veil" in game.last_update[0].keys():
            state["update_emoji"] = self.emoji    
            state["update_text"] += f" {game.last_update[0]['batter']}'s will manifests on {base_string(game.last_update[1])} base."

class HeatWave(Weather):
    def __init__(self,game):
        self.name = "Heat Wave"
        self.emoji = "🌄"

        self.counter_away = random.randint(2,4)
        self.counter_home = random.randint(2,4)

        self.swapped_pitcher_data = None

    def on_flip_inning(self, game):
        original_pitcher = game.get_pitcher()
        if game.top_of_inning:
            bat_team = game.teams["home"]
            counter = self.counter_home
        else:
            bat_team = game.teams["away"]
            counter = self.counter_away

        if game.inning == counter:
            if game.top_of_inning:
                self.counter_home = self.counter_home - (self.counter_home % 5) + 5 + random.randint(1,4) #rounds down to last 5, adds up to next 5. then adds a random number 2<=x<=5 to determine next pitcher                       
            else:
                self.counter_away = self.counter_away - (self.counter_away % 5) + 5 + random.randint(1,4)      

            #swap, accounting for teams where where someone's both batter and pitcher
            tries = 0
            while game.get_pitcher() == original_pitcher and tries < 3:
                bat_team.set_pitcher(use_lineup = True)
                tries += 1
            if game.get_pitcher() != original_pitcher:
                self.swapped_pitcher_data = (original_pitcher, game.get_pitcher())

    def modify_top_of_inning_message(self, game, state):
        if self.swapped_pitcher_data:
            original, sub = self.swapped_pitcher_data
            self.swapped_pitcher_data = None
            state["update_emoji"] = self.emoji
            state["update_text"] += f' {original} is exhausted from the heat. {sub} is forced to pitch!'
             
                

class Drizzle(Weather):
    def __init__(self,game):
        self.name = "Drizzle"
        self.emoji = "🌧"

    def on_flip_inning(self, game):
        if game.top_of_inning:
            next_team = "away"
        else:
            next_team = "home"

        lineup = game.teams[next_team].lineup
        game.bases[2] = lineup[(game.teams[next_team].lineup_position-1) % len(lineup)]

    def modify_top_of_inning_message(self, game, state):
        if game.top_of_inning:
            next_team = "away"
        else:
            next_team = "home"

        placed_player = game.teams[next_team].lineup[(game.teams[next_team].lineup_position-1) % len(game.teams[next_team].lineup)]

        state["update_emoji"] = self.emoji
        state["update_text"] += f' Due to inclement weather, {placed_player.name} is placed on second base.'


class Sun2(Weather):
    def __init__(self, game):
        self.name = "Sun 2"


    def activate(self, game):
        for teamtype in game.teams:
            team = game.teams[teamtype]
            if team.score >= 10:
                team.score -= 10
            # no win counting yet :(
            result.clear()
            result.update({
                "text": "The {} collect 10! Sun 2 smiles.".format(team.name),
                "text_only": True,
                "weather_message": True
            })

class Breezy(Weather):
    def __init__(self, game):
        self.name = "Breezy"
        self.emoji = "🎐"
        self.activation_chance = 0.05

    def activate(self, game, result):
        if random.random() < self.activation_chance:
            teamtype = random.choice(["away","home"])
            team = game.teams[teamtype]
            player = random.choice(team.lineup)
            old_player_name = player.name
            if ' ' in player.name:
                names = player.name.split(" ")
                first_first_letter = names[0][0]
                last_first_letter = names[-1][0]
                names[0] = last_first_letter + names[0][1:]
                names[-1] = first_first_letter + names[-1][1:]
                player.name = ' '.join(names)
            else:
                #name is one word, so turn 'bartholemew' into 'martholebew'
                first_letter = player.name[0]
                last_letter = player.name[-1]
                player.name = last_letter + player.name[1:-1] + last_letter

            book_adjectives = ["action-packed", "historical", "friendly", "rude", "mystery", "thriller", "horror", "sci-fi", "fantasy", "spooky","romantic"]
            book_types = ["novel","novella","poem","anthology","fan fiction","tablet","carving", "autobiography"]
            book = "{} {}".format(random.choice(book_adjectives),random.choice(book_types))

            result.clear()
            result.update({
                "text": "{} stopped to read a {} and became Literate! {} is now {}!".format(old_player_name, book, old_player_name, player.name),
                "text_only": True,
                "weather_message": True
            })

class BigFans(Weather):
    def __init__(self,game):
        self.name = "Big Fans"
        self.emoji = "🌬️"
        self.choose_sponsor(game)

        self.made_initial_announcement = False

    bonusPleasings = {
                    appearance_outcomes.single: "S",
                    appearance_outcomes.double: "D",
                    appearance_outcomes.triple: "T",
                    appearance_outcomes.homerun: "D",
                    appearance_outcomes.grandslam: "G"}

    def choose_sponsor(self, game):
        # choose a sponsor to ensure at least one batter in this game will please the sponsor
        all_first_characters = [player.name[0] for player in game.teams["home"].lineup] + [player.name[0] for player in game.teams["away"].lineup]
        self.sponsor = random.choice(all_first_characters).upper()

        sponsor_type = "character"
        if self.sponsor in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            sponsor_type = "letter"
        if self.sponsor.isnumeric():
            sponsor_type = "number"
        
        superlative = random.choice(("","","","","","","illustrious","radiant","gross","humble","tricky","world-famous","honestly slightly scared", "dishonest", "manipulative", "popular", "famous", "",""))
        if superlative != "":
          superlative += " "
        self.sponsor_title = "the {}{} {}".format(superlative,sponsor_type, self.sponsor)

    def activate(self, game, result):
        if not self.made_initial_announcement:
            self.made_initial_announcement = True
            result.clear()
            result.update({
                "text": f"This game was brought to you by viewers like you and {self.sponsor_title}.",
                "text_only": True,
                "weather_message": True,
            })
            return

        if result["ishit"]:
            battername = result["batter"].name #player whose name starts with S pleases letter S
            pleased_from_action = result["text"] in self.bonusPleasings and self.sponsor == self.bonusPleasings[result["text"]] # letter D is pleased by doubles, S for singles, T for triples...
            

            if battername.upper().startswith(self.sponsor) or pleased_from_action: 
                result["sponsorhappy"] = True

    def modify_atbat_message(self, game, state):
        if "sponsorhappy" in game.last_update[0].keys():
            state["update_emoji"] = self.emoji    
            state["update_text"] += f" This pleases {self.sponsor_title}!"

    def modify_top_of_inning_message(self, game, state):
        if game.inning > 1 and random.random() < 0.2:
            state["update_text"] += f' This game was brought to you by {self.sponsor_title}.'

class Feedback(Weather):
    def __init__(self, game):
        self.name = "Feedback"
        self.emoji = "🎤"
        self.activation_chance = 0.02
        self.swap_batter_vs_pitcher_chance = 0.8

    def activate(self, game, result):
        if random.random() < self.activation_chance:
            # feedback time
            player1 = None
            player2 = None
            team1 = game.teams["home"]
            team2 = game.teams["away"]
            if random.random() < self.swap_batter_vs_pitcher_chance:
                # swapping batters
                # theoretically this could swap players already on base :(
                team1 = game.teams["home"]
                team2 = game.teams["away"]
                homePlayerIndex = random.randint(0,len(team1.lineup)-1)
                awayPlayerIndex = random.randint(0,len(team2.lineup)-1)

                player1 = team1.lineup[homePlayerIndex]
                player2 = team2.lineup[awayPlayerIndex]

                team1.lineup[homePlayerIndex] = player2
                team2.lineup[awayPlayerIndex] = player1
            else:
                # swapping pitchers
                player1 = team1.pitcher
                player2 = team2.pitcher

                team1.pitcher = player2
                team2.pitcher = player1

            result.clear()
            result.update({
                "text": "{} and {} switched teams in the feedback!".format(player1.name,player2.name),
                "text_only": True,
                "weather_message": True,
            })

def all_weathers():
    weathers_dic = {
            "Supernova" : Supernova,
            "Midnight": Midnight,
            "Slight Tailwind": SlightTailwind,
            "Heavy Snow": HeavySnow,
            "Twilight" : Twilight, 
            "Thinned Veil" : ThinnedVeil,
            "Heat Wave" : HeatWave,
            "Drizzle" : Drizzle,
#        "Sun 2": Sun2,
            "Feedback": Feedback,
            "Breezy": Breezy,
            "Big Fans":BigFans,
        }
    return weathers_dic

