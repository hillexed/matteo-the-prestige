class player(object):
    def __init__(self, json_string):
        self.stlats = json.loads(json_string)
        self.id = self.stlats["id"]
        self.name = self.stlats["name"] # can be changed during a game
        self.original_name = self.stlats["name"] #doesn't change, used for statkeeping
        self.game_stats = {
                            "outs_pitched" : 0,
                            "walks_allowed" : 0,
                            "hits_allowed" : 0,
                            "strikeouts_given" : 0,
                            "runs_allowed" : 0,
                            "plate_appearances" : 0,
                            "walks_taken" : 0,
                            "sacrifices" : 0,
                            "hits" : 0,
                            "home_runs" : 0,
                            "total_bases" : 0,
                            "rbis" : 0,
                            "strikeouts_taken" : 0
            }

    def star_string(self, key):
        str_out = ""
        starstring = str(self.stlats[key])
        if ".5" in starstring:
            starnum = int(starstring[0])
            addhalf = True
        else:
            starnum = int(starstring[0])
            addhalf = False
        str_out += "⭐" * starnum
        if addhalf:
            str_out += "✨"
        return str_out

    def __str__(self):
        return self.name



class team(object):
    def __init__(self):
        self.name = None
        self.lineup = []
        self.lineup_position = 0
        self.rotation = []
        self.pitcher = None
        self.score = 0
        self.slogan = None

    def find_player(self, name):
        for index in range(0,len(self.lineup)):
            if self.lineup[index].name == name:
                return (self.lineup[index], index, self.lineup)
        for index in range(0,len(self.rotation)):
            if self.rotation[index].name == name:
                return (self.rotation[index], index, self.rotation)
        else:
            return (None, None, None)

    def get_emoji(self):
        # return the first character in a slogan, or "" if they don't have one
        not_emoji_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ.:\"'“"
        if len(self.slogan.strip()) == 0:
            return ""
        possible_emoji = self.slogan.strip()[0]
        if possible_emoji.upper() in not_emoji_chars:
            return ""
        return possible_emoji

    def find_player_spec(self, name, roster):
         for s_index in range(0,len(roster)):
            if roster[s_index].name == name:
                return (roster[s_index], s_index)

    def average_stars(self):
        total_stars = 0
        for _player in self.lineup:
            total_stars += _player.stlats["batting_stars"]
        for _player in self.rotation:
            total_stars += _player.stlats["pitching_stars"]
        return total_stars/(len(self.lineup) + len(self.rotation))

    def swap_player(self, name):
        this_player, index, roster = self.find_player(name)
        if this_player is not None and len(roster) > 1:
            if roster == self.lineup:
                if self.add_pitcher(this_player):
                    roster.pop(index)
                    return True
            else:
                if self.add_lineup(this_player)[0]:
                    self.rotation.pop(index)
                    return True
        return False

    def delete_player(self, name):
        this_player, index, roster = self.find_player(name)
        if this_player is not None and len(roster) > 1:
            roster.pop(index)
            return True
        else:
            return False

    def slide_player(self, name, new_spot):
        this_player, index, roster = self.find_player(name)
        if this_player is not None and new_spot <= len(roster):
            roster.pop(index)
            roster.insert(new_spot-1, this_player)
            return True
        else:
            return False

    def slide_player_spec(self, this_player_name, new_spot, roster):
        index = None
        for s_index in range(0,len(roster)):
            if roster[s_index].name == this_player_name:
                index = s_index
                this_player = roster[s_index]
        if index is None:
            return False
        elif new_spot <= len(roster):
            roster.pop(index)
            roster.insert(new_spot-1, this_player)
            return True
        else:
            return False
                
    def add_lineup(self, new_player):
        if len(self.lineup) < 20:
            self.lineup.append(new_player)
            return (True,)
        else:
            return (False, "20 players in the lineup, maximum. We're being really generous here.")
    
    def add_pitcher(self, new_player):
        if len(self.rotation) < 8:
            self.rotation.append(new_player)
            return True
        else:
            return False

    def set_pitcher(self, rotation_slot = None, use_lineup = False):
        temp_rotation = self.rotation.copy()
        if use_lineup:         
            for batter in self.lineup:
                temp_rotation.append(batter)
        if rotation_slot is None:
            self.pitcher = random.choice(temp_rotation)
        else:
            self.pitcher = temp_rotation[(rotation_slot-1) % len(temp_rotation)]

    def is_ready(self):
        try:
            return (len(self.lineup) >= 1 and len(self.rotation) > 0)
        except AttributeError:
            self.rotation = [self.pitcher]
            self.pitcher = None
            return (len(self.lineup) >= 1 and len(self.rotation) > 0)

    def prepare_for_save(self):
        self.lineup_position = 0
        self.score = 0
        if self.pitcher is not None and self.pitcher not in self.rotation:
            self.rotation.append(self.pitcher)
        self.pitcher = None
        for this_player in self.lineup:
            for stat in this_player.game_stats.keys():
                this_player.game_stats[stat] = 0
        for this_player in self.rotation:
            for stat in this_player.game_stats.keys():
                this_player.game_stats[stat] = 0
        return self

    def finalize(self):
        if self.is_ready():
            if self.pitcher == None:
                self.set_pitcher()
            while len(self.lineup) <= 4:
                self.lineup.append(random.choice(self.lineup))       
            return self
        else:
            return False

def get_team(name):
    try:
        team_json = jsonpickle.decode(db.get_team(name)[0], keys=True, classes=team)
        if team_json is not None:
            if team_json.pitcher is not None: #detects old-format teams, adds pitcher
                team_json.rotation.append(team_json.pitcher)
                team_json.pitcher = None
                update_team(team_json)
            return team_json
        return None
    except AttributeError:
        team_json.rotation = []
        team_json.rotation.append(team_json.pitcher)
        team_json.pitcher = None
        update_team(team_json)
        return team_json
    except:
        return None

def get_team_and_owner(name):
    try:
        counter, name, team_json_string, timestamp, owner_id = db.get_team(name, owner=True)
        team_json = jsonpickle.decode(team_json_string, keys=True, classes=team)
        if team_json is not None:
            if team_json.pitcher is not None: #detects old-format teams, adds pitcher
                team_json.rotation.append(team_json.pitcher)
                team_json.pitcher = None
                update_team(team_json)
            return (team_json, owner_id)
        return None
    except AttributeError:
        team_json.rotation = []
        team_json.rotation.append(team_json.pitcher)
        team_json.pitcher = None
        update_team(team_json)
        return (team_json, owner_id)
    except:
        return None

def save_team(this_team, user_id):
    try:
        this_team.prepare_for_save()
        team_json_string = jsonpickle.encode(this_team, keys=True)
        db.save_team(this_team.name, team_json_string, user_id)
        return True
    except:
        return None

def update_team(this_team):
    try:
        this_team.prepare_for_save()
        team_json_string = jsonpickle.encode(this_team, keys=True)
        db.update_team(this_team.name, team_json_string)
        return True
    except:
        return None

def get_all_teams():
    teams = []
    for team_pickle in db.get_all_teams():
        this_team = jsonpickle.decode(team_pickle[0], keys=True, classes=team)
        teams.append(this_team)
    return teams

def search_team(search_term):
    teams = []
    for team_pickle in db.search_teams(search_term):
        team_json = jsonpickle.decode(team_pickle[0], keys=True, classes=team)
        try:         
            if team_json.pitcher is not None:
                if len(team_json.rotation) == 0: #detects old-format teams, adds pitcher
                    team_json.rotation.append(team_json.pitcher)
                    team_json.pitcher = None
                    update_team(team_json)
        except AttributeError:
            team_json.rotation = []
            team_json.rotation.append(team_json.pitcher)
            team_json.pitcher = None
            update_team(team_json)
        except:
            return None

        teams.append(team_json)
    return teams
