import json, random, os, math, jsonpickle
import database as db
import weather
from gametext import base_string, appearance_outcomes

data_dir = "data"
games_config_file = os.path.join(data_dir, "games_config.json")

def config():
    if not os.path.exists(os.path.dirname(games_config_file)):
        os.makedirs(os.path.dirname(games_config_file))
    if not os.path.exists(games_config_file):
        #generate default config
        config_dic = {
                "default_length" : 3,
                "stlat_weights" : {
                        "batting_stars" : 1, #batting
                        "pitching_stars" : 0.8, #pitching
                        "baserunning_stars" : 1, #baserunning
                        "defense_stars" : 1 #defense
                    },
                "stolen_base_chance_mod" : 1,
                "stolen_base_success_mod" : 1,
            }
        with open(games_config_file, "w") as config_file:
            json.dump(config_dic, config_file, indent=4)
            return config_dic
    else:
        with open(games_config_file) as config_file:
            return json.load(config_file)


class game(object):

    def __init__(self, team1, team2, length=None):
        self.over = False
        self.teams = {"away" : team1, "home" : team2}
        self.inning = 1
        self.outs = 0
        self.top_of_inning = True
        self.last_update = ({},0) #this is a ({outcome}, runs) tuple
        self.play_has_begun = False
        self.owner = None
        self.victory_lap = False
        if length is not None:
            self.max_innings = length
        else:
            self.max_innings = config()["default_length"]
        self.bases = {1 : None, 2 : None, 3 : None}
        self.weather = weather.Weather(self)
        self.current_batter = None

    def choose_next_batter(self):
        if self.top_of_inning:
            bat_team = self.teams["away"]
        else:
            bat_team = self.teams["home"]

        self.current_batter = bat_team.lineup[bat_team.lineup_position % len(bat_team.lineup)]
        self.weather.on_choose_next_batter(self)

    def get_batter(self):
        if self.current_batter == None:
            self.choose_next_batter()
        return self.current_batter

    def get_pitcher(self):
        if self.top_of_inning:
            return self.teams["home"].pitcher
        else:
            return self.teams["away"].pitcher

    def at_bat(self):
        outcome = {}
        pitcher = self.get_pitcher()
        batter = self.get_batter()

        if self.top_of_inning:
            defender_list = self.teams["home"].lineup.copy()
        else:
            defender_list = self.teams["away"].lineup.copy()

        defender_list.append(pitcher)
        defender = random.choice(defender_list) #make pitchers field

        outcome["batter"] = batter
        outcome["defender"] = ""

        player_rolls = {}
        player_rolls["bat_stat"] = random_star_gen("batting_stars", batter)
        player_rolls["pitch_stat"] = random_star_gen("pitching_stars", pitcher)

        self.weather.modify_atbat_stats(player_rolls)

        roll = {}
        roll["pb_system_stat"] = (random.gauss(1*math.erf((player_rolls["bat_stat"] - player_rolls["pitch_stat"])*1.5)-1.8,2.2))
        roll["hitnum"] = random.gauss(2*math.erf(player_rolls["bat_stat"]/4)-1,3)

        self.weather.modify_atbat_roll(outcome, roll, defender)

        outcome["bases_advanced"] = 0

        if roll["pb_system_stat"] > 0:  #hit!
            outcome["ishit"] = True
            if roll["hitnum"] < 1:
                outcome["text"] = appearance_outcomes.single
                outcome["bases_advanced"] = 1
            elif roll["hitnum"] < 2.85 or "error" in outcome.keys():
                outcome["text"] = appearance_outcomes.double
                outcome["bases_advanced"] = 2
            elif roll["hitnum"] < 3.1:
                outcome["text"] = appearance_outcomes.triple
                outcome["bases_advanced"] = 3
            else:
                outcome["bases_advanced"] = 4
                if all([base is not None for base in self.bases.values()]):
                    outcome["text"] = appearance_outcomes.grandslam
                else:
                    outcome["text"] = appearance_outcomes.homerun

        else: #not a hit...
            outcome["ishit"] = False
            outcome["bases_advanced"] = 0
            if roll["hitnum"] < -1.5:
                outcome["text"] = random.choice([appearance_outcomes.strikeoutlooking, appearance_outcomes.strikeoutswinging])
            elif roll["hitnum"] < 1:
                outcome["text"] = appearance_outcomes.groundout
                outcome["defender"] = defender
            elif roll["hitnum"] < 4: 
                outcome["text"] = appearance_outcomes.flyout
                outcome["defender"] = defender
                if roll["hitnum"] < 2.5: #well hit flyouts can lead to sacrifice flies/advanced runners
                    if any([self.bases[base_num] for base_num in self.bases if base_num != 1]):
                        outcome["advance"] = True
                        outcome["bases_advanced"] = 1
            else:
                outcome["text"] = appearance_outcomes.walk

            if self.bases[1] is not None and roll["hitnum"] < -2 and self.outs != 2:
                outcome["text"] = appearance_outcomes.doubleplay
                outcome["defender"] = ""
                outcome["bases_advanced"] = 0

            runners = [(0,self.get_batter())]
            for base in range(1,4):
                if self.bases[base] == None:
                    break
                runners.append((base, self.bases[base]))
            outcome["runners"] = runners #list of consecutive baserunners: (base number, player object)

            if self.outs < 2 and len(runners) > 1: #fielder's choice replaces not great groundouts if any forceouts are present
                def_stat = random_star_gen("defense_stars", defender)
                if -1.5 <= roll["hitnum"] and roll["hitnum"] < -0.5: #poorly hit groundouts
                    outcome["text"] = appearance_outcomes.fielderschoice
                    outcome["defender"] = ""
                    outcome["bases_advanced"] = 1

        return outcome

    def thievery_attempts(self): #returns either false or "at-bat" outcome
        thieves = []
        attempts = []
        for base in self.bases.keys():
            if self.bases[base] is not None and base != 3: #no stealing home in simsim, sorry stu
                if self.bases[base+1] is None: #if there's somewhere to go
                    thieves.append((self.bases[base], base))
        for baserunner, start_base in thieves:
            stats = {
                "run_stars": random_star_gen("baserunning_stars", baserunner)*config()["stolen_base_chance_mod"],
                "def_stars": random_star_gen("defense_stars", self.get_pitcher())
            }

            self.weather.modify_steal_stats(stats)

            if stats["run_stars"] >= (stats["def_stars"] - 1.5): #if baserunner isn't worse than pitcher
                roll = random.random()
                if roll >= (-(((stats["run_stars"]+1)/14)**2)+1): #plug it into desmos or something, you'll see
                    attempts.append((baserunner, start_base))

        if len(attempts) == 0:
            return False
        else:     
            return (self.steals_check(attempts), 0) #effectively an at-bat outcome with no score

    def steals_check(self, attempts):
        if self.top_of_inning:
            defense_team = self.teams["home"]
        else:
            defense_team = self.teams["away"]

        outcome = {}
        outcome["steals"] = []

        for baserunner, start_base in attempts:
            defender = random.choice(defense_team.lineup) #excludes pitcher
            run_stat = random_star_gen("baserunning_stars", baserunner)
            def_stat = random_star_gen("defense_stars", defender)
            run_roll = random.gauss(2*math.erf((run_stat-def_stat)/4)-1,3)*config()["stolen_base_success_mod"]
            if start_base >= 2:
                run_roll = run_roll * .9 #stealing third is harder
            if run_roll < 1:
                outcome["steals"].append(f"{baserunner} was caught stealing {base_string(start_base+1)} base by {defender}!")
                self.get_pitcher().game_stats["outs_pitched"] += 1
                self.outs += 1
            else:
                outcome["steals"].append(f"{baserunner} steals {base_string(start_base+1)} base!")
                self.bases[start_base+1] = baserunner
            self.bases[start_base] = None

        if self.outs >= 3:
            self.flip_inning()

        return outcome


    def calc_baserunning_difficulty(self, start_base_num, bases_advanced, outcome={}):
        baserunning_roll_threshold = 1
        if start_base_num == 1:
            baserunning_roll_threshold = 0 #running from first to second is easy

        if bases_advanced >= 2:
            baserunning_roll_threshold = 1 #running from first to home off a double or triple is pretty hard
        else: # bases_advanced = 1, advancing off a single
            if start_base_num == 2:
                baserunning_roll_threshold = 0 #running from second to home off a single
            elif start_base_num == 1:
                baserunning_roll_threshold = 0.75 #running from first to third is a bit harder


        if "advance" in outcome.keys():
            if start_base_num == 3:
                baserunning_roll_threshold = -500 #guaranteed to go home
            else:
                baserunning_roll_threshold = 2 #have to work for it

        if outcome["text"] == appearance_outcomes.groundout or outcome["text"] == appearance_outcomes.doubleplay:
            if start_base_num == 3:
                baserunning_roll_threshold = -500 #guaranteed to go home
            elif start_base_num == 2:
                baserunning_roll_threshold = 1.5
                if outcome["text"] == appearance_outcomes.doubleplay:
                    baserunning_roll_threshold = -500 #double play gives them time to run, guaranteed
          
        return baserunning_roll_threshold

    def baserunner_check(self, defender, outcome):
        def_stat = random_star_gen("defense_stars", defender)
        if outcome["text"] == appearance_outcomes.homerun or outcome["text"] == appearance_outcomes.grandslam:
            runs = 1
            for base_id in self.bases:
                if self.bases[base_id] is not None:
                    runs += 1
                self.bases[base_id] = None
            if "veil" in outcome.keys():
                if runs < 4:
                    self.bases[runs] = self.get_batter()
                else:
                    runs += 1
            return runs

        batter_made_it_on_base = True


        if "advance" in outcome.keys():
            runs = 0
            batter_made_it_on_base = False

            if self.bases[3] is not None:
                outcome["text"] = appearance_outcomes.sacrifice
                self.get_batter().game_stats["sacrifices"] += 1

        if outcome["text"] == appearance_outcomes.fielderschoice:
            furthest_base, runner = outcome["runners"].pop() #get furthest baserunner
            self.bases[furthest_base] = None 
            outcome["fc_out"] = (runner.name, base_string(furthest_base+1)) #runner thrown out
            # others advance as normal

        runs = 0
        if "bases_advanced" in outcome:
            bases_advanced = outcome["bases_advanced"]
        else: #something's gone wrong
            bases_advanced = 1

        for base_num in range(len(self.bases),0,-1): #base_num = 3,2,1. once per baserunner
            if self.bases[base_num] is not None: #there's a runner here!
                base_reached = base_num + bases_advanced

                # chance to run an extra base
                run_roll = random.gauss(math.erf(random_star_gen("baserunning_stars", self.bases[base_num])-def_stat)-.5,1.5)


                bonus_base_threshold = calc_baserunning_difficulty(self, start_base_num, bases_advanced)
                # if your baserunning is good enough, you advance an extra base
                if run_roll > bonus_base_threshold and base_reached+1 in self.bases and self.bases[base_reached+1] is None:
                    base_reached += 1

                if base_reached > len(self.bases): #runner reached home!
                    runs += 1
                else: #runner is running, but not all the way to home
                    self.bases[base_reached] = self.bases[base_num]

                self.bases[base_num] = None


        if batter_made_it_on_base:
            self.bases[bases_advanced] = self.get_batter() #batter moves up

        return runs


    def batterup(self):
        scores_to_add = 0
        result = self.at_bat()

        self.weather.activate(self, result) # possibly modify result in-place

        if "text_only" in result:
            return (result, 0)            
    
        if self.top_of_inning:
            offense_team = self.teams["away"]
            defense_team = self.teams["home"]
        else:
            offense_team = self.teams["home"]
            defense_team = self.teams["away"]


        defenders = defense_team.lineup.copy()
        defenders.append(defense_team.pitcher)
        defender = random.choice(defenders) #pitcher can field outs now :3

        if result["ishit"]: #if batter gets a hit:
            self.get_batter().game_stats["hits"] += 1
            self.get_pitcher().game_stats["hits_allowed"] += 1

            if result["text"] == appearance_outcomes.single:
                self.get_batter().game_stats["total_bases"] += 1               
            elif result["text"] == appearance_outcomes.double:
                self.get_batter().game_stats["total_bases"] += 2
            elif result["text"] == appearance_outcomes.triple:
                self.get_batter().game_stats["total_bases"] += 3
            elif result["text"] == appearance_outcomes.homerun or result["text"] == appearance_outcomes.grandslam:
                self.get_batter().game_stats["total_bases"] += 4
                self.get_batter().game_stats["home_runs"] += 1



            scores_to_add += self.baserunner_check(defender, result)

        else: #batter did not get a hit
            if result["text"] == appearance_outcomes.walk:
                walkers = [(0,self.get_batter())]
                for base in range(1,4):
                    if self.bases[base] == None:
                        break
                    walkers.append((base, self.bases[base]))
                for i in range(0, len(walkers)):
                    this_walker = walkers.pop()
                    if this_walker[0] == 3:
                        self.bases[3] = None
                        scores_to_add += 1
                    else:
                        self.bases[this_walker[0]+1] = this_walker[1] #this moves all consecutive baserunners one forward

                self.get_batter().game_stats["walks_taken"] += 1
                self.get_pitcher().game_stats["walks_allowed"] += 1
            
            elif result["text"] == appearance_outcomes.doubleplay:
                self.get_pitcher().game_stats["outs_pitched"] += 2
                self.outs += 2
                self.bases[1] = None     
                if self.outs < 3:
                    scores_to_add += self.baserunner_check(defender, result)
                    self.get_batter().game_stats["rbis"] -= scores_to_add #remove the fake rbi from the player in advance

            elif result["text"] == appearance_outcomes.fielderschoice or result["text"] == appearance_outcomes.groundout:
                self.get_pitcher().game_stats["outs_pitched"] += 1
                self.outs += 1
                if self.outs < 3:
                    scores_to_add += self.baserunner_check(defender, result)

            elif "advance" in result.keys():
                self.get_pitcher().game_stats["outs_pitched"] += 1
                self.outs += 1
                if self.outs < 3:
                    if self.bases[3] is not None:
                        self.get_batter().game_stats["sacrifices"] += 1
                    scores_to_add += self.baserunner_check(defender, result)

            elif result["text"] == appearance_outcomes.strikeoutlooking or result["text"] == appearance_outcomes.strikeoutswinging:
                self.get_pitcher().game_stats["outs_pitched"] += 1
                self.outs += 1
                self.get_batter().game_stats["strikeouts_taken"] += 1
                self.get_pitcher().game_stats["strikeouts_given"] += 1

            else: 
                self.get_pitcher().game_stats["outs_pitched"] += 1
                self.outs += 1

        self.get_batter().game_stats["plate_appearances"] += 1
        
        if self.outs < 3:
            offense_team.score += scores_to_add #only add points if inning isn't over
        else:
            scores_to_add = 0
        self.get_batter().game_stats["rbis"] += scores_to_add
        self.get_pitcher().game_stats["runs_allowed"] += scores_to_add
        offense_team.lineup_position += 1 #put next batter up
        self.choose_next_batter()
        if self.outs >= 3:
            self.flip_inning()
            
         

        return (result, scores_to_add) #returns ab information and scores

    def flip_inning(self):
        for base in self.bases.keys():
            self.bases[base] = None
        self.outs = 0

        self.top_of_inning = not self.top_of_inning

        self.weather.on_flip_inning(self)

        self.choose_next_batter()

        if self.top_of_inning:
            self.inning += 1
            if self.inning > self.max_innings and self.teams["home"].score != self.teams["away"].score: #game over
                self.over = True


    def end_of_game_report(self):
        return {
                "away_team" : self.teams["away"],
                "away_pitcher" : self.teams["away"].pitcher,
                "home_team" : self.teams["home"],
                "home_pitcher" : self.teams["home"].pitcher
            }

    def named_bases(self):
        name_bases = {}
        for base in range(1,4):
            if self.bases[base] is not None:
                name_bases[base] = self.bases[base].name
            else:
                name_bases[base] = None

        return name_bases


    def gamestate_update_full(self):
        self.play_has_begun = True
        attempts = self.thievery_attempts()
        if attempts == False:
            self.last_update = self.batterup()
        else:
            self.last_update = attempts
        return self.gamestate_display_full()

    def gamestate_display_full(self):
        if not self.over:
            return "Still in progress."
        else:
            return f"""Game over! Final score: **{self.teams['away'].score} - {self.teams['home'].score}**"""

    def add_stats(self):
        players = self.get_stats()
        db.add_stats(players)

    def get_stats(self):
        players = []
        for this_player in self.teams["away"].lineup:
            players.append((this_player.original_name, this_player.game_stats))
        for this_player in self.teams["home"].lineup:
            players.append((this_player.original_name, this_player.game_stats))
        players.append((self.teams["home"].pitcher.original_name, self.teams["home"].pitcher.game_stats))
        players.append((self.teams["away"].pitcher.original_name, self.teams["away"].pitcher.game_stats))
        return players

    def get_team_specific_stats(self):
        players = {
            self.teams["away"].name : [],
            self.teams["home"].name : []
            }
        for this_player in self.teams["away"].lineup:
            players[self.teams["away"].name].append((this_player.original_name, this_player.game_stats))
        for this_player in self.teams["home"].lineup:
            players[self.teams["home"].name].append((this_player.original_name, this_player.game_stats))
        players[self.teams["home"].name].append((self.teams["home"].pitcher.original_name, self.teams["home"].pitcher.game_stats))
        players[self.teams["away"].name].append((self.teams["away"].pitcher.original_name, self.teams["away"].pitcher.game_stats))
        return players
        


def random_star_gen(key, player):
    return random.gauss(config()["stlat_weights"][key] * player.stlats[key],1)
#    innings_pitched
#    walks_allowed
#    strikeouts_given
#    runs_allowed
#    plate_appearances
#    walks
#    hits
#    total_bases
#    rbis
#    walks_taken
#    strikeouts_taken


