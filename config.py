import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///reputation.db')

# Reputation System
STARTING_REPUTATION = float(os.getenv('STARTING_REPUTATION', '2.0'))
REPUTATION_CHANGE = float(os.getenv('REPUTATION_CHANGE', '1.0'))  # Default amount to increase or decrease reputation
REPUTATION_COST = float(os.getenv('REPUTATION_COST', '0.5'))  # Cost in reputation for a user to affect another's reputation
COOLDOWN_HOURS = int(os.getenv('COOLDOWN_HOURS', '24'))  # Default cooldown in hours

CHANGE_AMOUNT = REPUTATION_CHANGE  # Added this for consistency

# Role Thresholds
ROLE_THRESHOLDS = {
    "Novice": float(os.getenv('NOVICE_THRESHOLD', '3.0')),
    "Expert": float(os.getenv('EXPERT_THRESHOLD', '5.0')),
    "Master": float(os.getenv('MASTER_THRESHOLD', '7.0'))
}

# Reputation Gravitation
GRAVITY_CENTER = float(os.getenv('GRAVITY_CENTER', '1.0'))  # The point towards which all reputations gravitate
POSITIVE_GRAVITATION_INCREMENT = float(os.getenv('POSITIVE_GRAVITATION_INCREMENT', '0.1'))  # Amount to decrease reputation above gravity center
NEGATIVE_GRAVITATION_INCREMENT = float(os.getenv('NEGATIVE_GRAVITATION_INCREMENT', '0.1'))  # Amount to increase reputation below gravity center
GRAVITATION_INTERVAL = int(os.getenv('GRAVITATION_INTERVAL', '10'))  # Interval in seconds (e.g., 3600 for hourly)