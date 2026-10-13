from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ROW_COUNT = 150
SEED = 20261014
BATTERS_BY_TEAM = {
    "India": ["Yashasvi Jaiswal", "Abhishek Sharma", "Ruturaj Gaikwad", "Tilak Varma", "Rinku Singh", "Sanju Samson", "Jitesh Sharma", "Rishabh Pant", "Sai Sudharsan", "Dhruv Jurel", "Riyan Parag", "Nitish Kumar Reddy", "Shivam Dube", "Devdutt Padikkal", "Sarfaraz Khan"],
    "Australia": ["Matthew Short", "Marnus Labuschagne", "Steve Smith", "Cameron Green", "Mitchell Marsh", "Alex Carey", "Josh Inglis", "Jake Fraser-McGurk", "Cooper Connolly", "Matt Renshaw", "Sam Konstas", "Beau Webster", "Tim David", "Glenn Maxwell", "Aaron Hardie"],
    "England": ["Harry Brook", "Joe Root", "Ben Duckett", "Zak Crawley", "Ollie Pope", "Jamie Smith", "Phil Salt", "Jamie Overton", "Jacob Bethell", "Will Jacks", "Tom Banton", "Liam Livingstone", "Rehan Ahmed", "Dan Lawrence", "Dan Mousley"],
    "New Zealand": ["Devon Conway", "Daryl Mitchell", "Rachin Ravindra", "Tom Latham", "Glenn Phillips", "Finn Allen", "Mark Chapman", "Will Young", "Michael Bracewell", "Mitchell Santner", "Henry Nicholls", "Tim Seifert", "Tom Blundell", "Cole McConchie", "Jimmy Neesham"],
    "South Africa": ["Aiden Markram", "Ryan Rickelton", "Tony de Zorzi", "Tristan Stubbs", "Dewald Brevis", "David Miller", "Heinrich Klaasen", "Quinton de Kock", "Reeza Hendricks", "Rassie van der Dussen", "Temba Bavuma", "Matthew Breetzke", "Kyle Verreynne", "Wiaan Mulder", "Jason Smith"],
    "Pakistan": ["Babar Azam", "Mohammad Rizwan", "Fakhar Zaman", "Saim Ayub", "Saud Shakeel", "Abdullah Shafique", "Salman Ali Agha", "Imam-ul-Haq", "Kamran Ghulam", "Mohammad Haris", "Sahibzada Farhan", "Usman Khan", "Khawaja Nafay", "Haseebullah Khan", "Omair Bin Yousuf"],
    "Bangladesh": ["Litton Das", "Najmul Hossain Shanto", "Towhid Hridoy", "Mehidy Hasan Miraz", "Tanzid Hasan", "Jaker Ali", "Parvez Hossain Emon", "Shahadat Hossain", "Mominul Haque", "Afif Hossain", "Shamim Hossain", "Zakir Hasan", "Saif Hassan", "Soumya Sarkar", "Tanzim Hasan Sakib"],
    "Sri Lanka": ["Pathum Nissanka", "Kusal Mendis", "Charith Asalanka", "Kamindu Mendis", "Sadeera Samarawickrama", "Kusal Perera", "Avishka Fernando", "Dhananjaya de Silva", "Janith Liyanage", "Nishan Madushka", "Pavan Rathnayake", "Dinesh Chandimal", "Oshada Fernando", "Nuwanidu Fernando", "Lasith Croospulle"],
    "West Indies": ["Shai Hope", "Evin Lewis", "Brandon King", "Rovman Powell", "Shimron Hetmyer", "Sherfane Rutherford", "Keacy Carty", "Johnson Charles", "Roston Chase", "Alick Athanaze", "Justin Greaves", "Jewel Andrew", "Kavem Hodge", "Kyle Mayers", "Matthew Forde"],
    "Afghanistan": ["Rahmanullah Gurbaz", "Ibrahim Zadran", "Rahmat Shah", "Hashmatullah Shahidi", "Azmatullah Omarzai", "Gulbadin Naib", "Mohammad Ishaq", "Sediqullah Atal", "Darwish Rasooli", "Ikram Alikhil", "Karim Janat", "Nangyal Kharoti", "Shahidullah Kamal", "Noor Ahmad", "Mujeeb Ur Rahman"],
}
BOWLERS_BY_TEAM = {
    "India": ["Jasprit Bumrah", "Mohammed Siraj", "Arshdeep Singh", "Kuldeep Yadav", "Ravi Bishnoi", "Varun Chakravarthy", "Axar Patel", "Ravindra Jadeja", "Washington Sundar", "Harshit Rana", "Prasidh Krishna", "Mukesh Kumar", "Akash Deep", "Mayank Yadav", "Avesh Khan"],
    "Australia": ["Pat Cummins", "Mitchell Starc", "Josh Hazlewood", "Nathan Lyon", "Adam Zampa", "Sean Abbott", "Spencer Johnson", "Lance Morris", "Xavier Bartlett", "Scott Boland", "Michael Neser", "Jhye Richardson", "Todd Murphy", "Cooper Connolly", "Ben Dwarshuis"],
    "England": ["Jofra Archer", "Mark Wood", "Gus Atkinson", "Brydon Carse", "Shoaib Bashir", "Adil Rashid", "Sam Curran", "Reece Topley", "John Turner", "Josh Tongue", "Saqib Mahmood", "Olly Stone", "Liam Dawson", "Tom Hartley", "Matt Potts"],
    "New Zealand": ["Matt Henry", "Will O'Rourke", "Lockie Ferguson", "Ben Sears", "Jacob Duffy", "Ish Sodhi", "Mitchell Santner", "Michael Bracewell", "Nathan Smith", "Kyle Jamieson", "Matt Fisher", "Adam Milne", "Zak Foulkes", "Blair Tickner", "Jayden Lennox"],
    "South Africa": ["Kagiso Rabada", "Anrich Nortje", "Marco Jansen", "Gerald Coetzee", "Keshav Maharaj", "Lungi Ngidi", "Tabraiz Shamsi", "Nandre Burger", "Lizaad Williams", "Wiaan Mulder", "Ottneil Baartman", "Corbin Bosch", "Bjorn Fortuin", "Kwena Maphaka", "Senuran Muthusamy"],
    "Pakistan": ["Shaheen Shah Afridi", "Naseem Shah", "Haris Rauf", "Abrar Ahmed", "Mohammad Wasim Jr", "Mohammad Nawaz", "Shadab Khan", "Usama Mir", "Hasan Ali", "Mohammad Abbas Afridi", "Mohammad Ali", "Aamer Jamal", "Khurram Shahzad", "Mir Hamza", "Noman Ali"],
    "Bangladesh": ["Taskin Ahmed", "Mustafizur Rahman", "Nahid Rana", "Tanzim Hasan Sakib", "Shoriful Islam", "Taijul Islam", "Mehidy Hasan Miraz", "Rishad Hossain", "Hasan Mahmud", "Rakibul Hasan", "Khaled Ahmed", "Nasum Ahmed", "Mukidul Islam", "Sumon Khan", "Tanvir Islam"],
    "Sri Lanka": ["Wanindu Hasaranga", "Maheesh Theekshana", "Matheesha Pathirana", "Dilshan Madushanka", "Dushmantha Chameera", "Asitha Fernando", "Lahiru Kumara", "Pramod Madushan", "Jeffrey Vandersay", "Dunith Wellalage", "Praveen Jayawickrama", "Kasun Rajitha", "Milan Rathnayake", "Nishan Peiris", "Eshan Malinga"],
    "West Indies": ["Alzarri Joseph", "Shamar Joseph", "Gudakesh Motie", "Akeal Hosein", "Jayden Seales", "Romario Shepherd", "Matthew Forde", "Shamar Springer", "Obed McCoy", "Roston Chase", "Jason Holder", "Kevin Sinclair", "Anderson Phillip", "Oshane Thomas", "Hayden Walsh"],
    "Afghanistan": ["Rashid Khan", "Mujeeb Ur Rahman", "Fazalhaq Farooqi", "Naveen-ul-Haq", "Noor Ahmad", "Azmatullah Omarzai", "Sediqullah Atal", "Qais Ahmad", "Ziaur Rahman Sharifi", "Fareed Ahmad", "Nangyal Kharoti", "Sharafuddin Ashraf", "Bilal Sami", "Wafadar Momand", "Yama Arab"],
}
TEAMS = list(BATTERS_BY_TEAM)
STADIUMS_BY_TEAM = {
    "India": ["Narendra Modi Stadium, Ahmedabad", "Wankhede Stadium, Mumbai", "Eden Gardens, Kolkata", "M. Chinnaswamy Stadium, Bengaluru", "MA Chidambaram Stadium, Chennai", "Arun Jaitley Stadium, Delhi", "Rajiv Gandhi International Cricket Stadium, Hyderabad"],
    "Australia": ["Melbourne Cricket Ground, Melbourne", "Sydney Cricket Ground, Sydney", "The Gabba, Brisbane", "Adelaide Oval, Adelaide", "Perth Stadium, Perth", "Bellerive Oval, Hobart", "Manuka Oval, Canberra"],
    "England": ["Lord's, London", "The Oval, London", "Edgbaston, Birmingham", "Headingley, Leeds", "Trent Bridge, Nottingham", "Old Trafford, Manchester"],
    "New Zealand": ["Eden Park, Auckland", "Hagley Oval, Christchurch", "Basin Reserve, Wellington", "Seddon Park, Hamilton", "Bay Oval, Mount Maunganui"],
    "South Africa": ["Newlands Cricket Ground, Cape Town", "Wanderers Stadium, Johannesburg", "SuperSport Park, Centurion", "Kingsmead, Durban", "St George's Park, Gqeberha"],
    "Pakistan": ["Gaddafi Stadium, Lahore", "National Bank Cricket Arena, Karachi", "Rawalpindi Cricket Stadium, Rawalpindi", "Multan Cricket Stadium, Multan"],
    "Bangladesh": ["Sher-e-Bangla National Cricket Stadium, Dhaka", "Zahur Ahmed Chowdhury Stadium, Chattogram", "Sylhet International Cricket Stadium, Sylhet"],
    "Sri Lanka": ["R. Premadasa Stadium, Colombo", "Pallekele International Cricket Stadium, Kandy", "Galle International Stadium, Galle", "Rangiri Dambulla International Stadium, Dambulla"],
    "West Indies": ["Kensington Oval, Bridgetown", "Queen's Park Oval, Port of Spain", "Sabina Park, Kingston", "Guyana National Stadium, Providence", "Sir Vivian Richards Stadium, North Sound", "Daren Sammy Cricket Ground, Gros Islet"],
    "Afghanistan": ["Sharjah Cricket Stadium, Sharjah", "Dubai International Cricket Stadium, Dubai", "Sheikh Zayed Cricket Stadium, Abu Dhabi"],
}
FORMATS = ("T20", "ODI", "Test")
BATTER_ROSTER = [(name, team) for team, names in BATTERS_BY_TEAM.items() for name in names]
BOWLER_ROSTER = [(name, team) for team, names in BOWLERS_BY_TEAM.items() for name in names]
BATTER_NAMES = [name for name, _ in BATTER_ROSTER]
BOWLER_NAMES = [name for name, _ in BOWLER_ROSTER]

MATCH_FIELDS = ["date", "format", "team", "opponent", "venue", "runs", "wickets", "overs", "run_rate", "result", "player_of_match"]
PLAYER_FIELDS = ["player", "team", "role", "matches", "runs", "average", "strike_rate", "fifties", "hundreds"]
BOWLER_FIELDS = ["bowler", "team", "matches", "innings", "overs", "runs_conceded", "wickets", "economy", "average", "strike_rate", "best_figures", "four_wicket_hauls", "five_wicket_hauls"]


def write_rows(filename: str, fields: list[str], rows: list[dict[str, object]]) -> None:
    with (DATA_DIR / filename).open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def player_record(role: str, index: int) -> tuple[str, str]:
    roster = BATTER_ROSTER if role == "Batter" else BOWLER_ROSTER
    return roster[index - 1]


def build_matches(rng: random.Random) -> list[dict[str, object]]:
    rows = []
    for index in range(1, ROW_COUNT + 1):
        team, opponent = rng.sample(TEAMS, 2)
        match_format = rng.choice(FORMATS)
        runs = rng.randint(90, 340)
        wickets = rng.randint(0, 10)
        overs = {"T20": 20, "ODI": 50, "Test": 90}[match_format]
        result_type = rng.choice(("Won by runs", "Won by wickets", "Lost by runs", "Lost by wickets", "Draw"))
        margin_limit = 10 if "wickets" in result_type else 250
        result = f"{result_type} {rng.randint(1, margin_limit)}" if result_type != "Draw" else "Draw"
        match_date = date(2020, 1, 1) + timedelta(days=rng.randint(0, 2400))
        available_players = [record for record in (*BATTER_ROSTER, *BOWLER_ROSTER) if record[1] in (team, opponent)]
        player_name, _ = rng.choice(available_players)
        available_venues = STADIUMS_BY_TEAM[team] + STADIUMS_BY_TEAM[opponent]
        rows.append({
            "date": match_date.isoformat(),
            "format": match_format,
            "team": team,
            "opponent": opponent,
            "venue": rng.choice(available_venues),
            "runs": runs,
            "wickets": wickets,
            "overs": overs,
            "run_rate": round(runs / overs, 2),
            "result": result,
            "player_of_match": player_name,
        })
    return rows


def build_players(rng: random.Random) -> list[dict[str, object]]:
    rows = []
    for index, (player, team) in enumerate(BATTER_ROSTER, start=1):
        matches = rng.randint(5, 50)
        average = round(rng.uniform(18, 62), 2)
        rows.append({
            "player": player,
            "team": team,
            "role": "Batter",
            "matches": matches,
            "runs": round(matches * average * rng.uniform(0.65, 1.4)),
            "average": average,
            "strike_rate": round(rng.uniform(65, 165), 2),
            "fifties": rng.randint(0, max(1, matches // 3)),
            "hundreds": rng.randint(0, max(1, matches // 12)),
        })
    return rows


def build_bowlers(rng: random.Random) -> list[dict[str, object]]:
    rows = []
    for index, (bowler, team) in enumerate(BOWLER_ROSTER, start=1):
        innings = rng.randint(5, 45)
        wickets = rng.randint(5, innings * 3)
        balls = rng.randint(innings * 18, innings * 36)
        conceded = rng.randint(wickets * 12, wickets * 32)
        completed_overs, remaining_balls = divmod(balls, 6)
        rows.append({
            "bowler": bowler,
            "team": team,
            "matches": max(innings, rng.randint(innings, 50)),
            "innings": innings,
            "overs": f"{completed_overs}.{remaining_balls}",
            "runs_conceded": conceded,
            "wickets": wickets,
            "economy": round(conceded / (balls / 6), 2),
            "average": round(conceded / wickets, 2),
            "strike_rate": round(balls / wickets, 2),
            "best_figures": f"{rng.randint(1, 6)}/{rng.randint(8, 55)}",
            "four_wicket_hauls": rng.randint(0, max(1, wickets // 8)),
            "five_wicket_hauls": rng.randint(0, max(1, wickets // 15)),
        })
    return rows


def main() -> None:
    for role, roster in (("batter", BATTER_ROSTER), ("bowler", BOWLER_ROSTER)):
        if len(roster) != ROW_COUNT or len({name for name, _ in roster}) != ROW_COUNT:
            raise ValueError(f"Expected {ROW_COUNT} unique current {role} names.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    write_rows("demo_matches.csv", MATCH_FIELDS, build_matches(rng))
    write_rows("demo_players.csv", PLAYER_FIELDS, build_players(rng))
    write_rows("demo_bowlers.csv", BOWLER_FIELDS, build_bowlers(rng))
    print(f"Wrote {ROW_COUNT} illustrative records to each of three demo CSV files in {DATA_DIR}.")


if __name__ == "__main__":
    main()
