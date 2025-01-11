import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///reputation.db')

# Reputation System
STARTING_REPUTATION = 0.0
REPUTATION_CHANGE = 1.0  # Default amount to increase or decrease reputation
REPUTATION_COST = 0.5  # Cost in reputation for a user to affect another's reputation
COOLDOWN_HOURS = 24  # Default cooldown in hours

CHANGE_AMOUNT = REPUTATION_CHANGE  # Added this for consistency

# Role Thresholds
ROLE_THRESHOLDS = {
    "Novice": 10,
    "Expert": 50,
    "Master": 100
}

# Feedback Configuration
FEEDBACK_CHANNEL_ID = int(os.getenv('FEEDBACK_CHANNEL_ID', 0))  # Replace 0 with a default channel ID if you have one

# Reputation Gravitation
GRAVITY_CENTER = float(os.getenv('GRAVITY_CENTER', '0.0'))  # The point towards which all reputations gravitate
POSITIVE_GRAVITATION_INCREMENT = float(os.getenv('POSITIVE_GRAVITATION_INCREMENT', '0.1'))  # Amount to decrease reputation above gravity center
NEGATIVE_GRAVITATION_INCREMENT = float(os.getenv('NEGATIVE_GRAVITATION_INCREMENT', '0.1'))  # Amount to increase reputation below gravity center
GRAVITATION_INTERVAL = int(os.getenv('GRAVITATION_INTERVAL', '3600'))  # Interval in seconds (e.g., 3600 for hourly)