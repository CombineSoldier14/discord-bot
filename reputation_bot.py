# reputation_bot.py

import discord
from discord import app_commands, Embed, Interaction, Member, Role, utils
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import logging
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from typing import Optional
import asyncio
from .config import BOT_TOKEN, GUILD_ID, DATABASE_URL, COOLDOWN_HOURS, REPUTATION_COST, CHANGE_AMOUNT, ROLE_THRESHOLDS, GRAVITY_CENTER, POSITIVE_GRAVITATION_INCREMENT, NEGATIVE_GRAVITATION_INCREMENT, GRAVITATION_INTERVAL, STARTING_REPUTATION

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Models
class UserReputation(Base):
    __tablename__ = 'user_reputations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    reputation = Column(Float, default=0.0)
    last_modified = Column(DateTime, server_default=func.now())

class ReputationChange(Base):
    __tablename__ = 'reputation_changes'
    
    id = Column(Integer, primary_key=True)
    source_user_id = Column(Integer, nullable=False)
    target_user_id = Column(Integer, nullable=False)
    change = Column(Float, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

Base.metadata.create_all(engine)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for member-related operations
client = commands.Bot(command_prefix='!', intents=intents)

# Helper function for database operations
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@tasks.loop(seconds=GRAVITATION_INTERVAL)
async def gravitation_task():
    db = next(get_db())
    try:
        users = db.query(UserReputation).all()
        for user in users:
            if user.reputation > GRAVITY_CENTER:
                # Reputation is above gravity center, gravitate downwards
                new_reputation = max(GRAVITY_CENTER, user.reputation - POSITIVE_GRAVITATION_INCREMENT)
            elif user.reputation < GRAVITY_CENTER:
                # Reputation is below gravity center, gravitate upwards
                new_reputation = min(GRAVITY_CENTER, user.reputation + NEGATIVE_GRAVITATION_INCREMENT)
            else:
                continue  # Reputation is already at the gravity center, no need to change

            if new_reputation != user.reputation:
                user.reputation = new_reputation
                # Optionally, log or notify if reputation changes to gravity center
                if user.reputation == GRAVITY_CENTER:
                    logger.info(f"User {user.user_id}'s reputation has reached the gravity center of {GRAVITY_CENTER} due to gravitation.")
            
        db.commit()
        logger.info("Reputation gravitation task completed.")
    except SQLAlchemyError as e:
        logger.error(f"Database Error during reputation gravitation: {e}")
    finally:
        db.close()

@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user.name}')
    try:
        await client.tree.sync(guild=discord.Object(id=GUILD_ID))
        logger.info(f"Slash commands synced to guild {GUILD_ID}")
        gravitation_task.start()
    except Exception as e:
        logger.error(f"Failed to sync commands or start tasks: {e}")

@client.tree.command(name="reputation", description="Manage user reputation", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.cooldown(1, COOLDOWN_HOURS * 3600, key=lambda i: (i.user.id, i.data.get('options', [])[0]['value'] if 'options' in i.data else None))
async def reputation(interaction: Interaction, user: Member, change: float = CHANGE_AMOUNT):
    if user.id == interaction.user.id:
        await interaction.response.send_message(embed=Embed(description="You cannot affect your own reputation.", color=discord.Color.red()))
        return

    db = next(get_db())
    try:
        source_user = db.query(UserReputation).filter_by(user_id=interaction.user.id).first()
        if not source_user:
            source_user = UserReputation(user_id=interaction.user.id, reputation=0.0)
            db.add(source_user)
        
        target_user = db.query(UserReputation).filter_by(user_id=user.id).first()
        if not target_user:
            target_user = UserReputation(user_id=user.id, reputation=0.0)
            db.add(target_user)

        if source_user.reputation < REPUTATION_COST:
            await interaction.response.send_message(embed=Embed(description="You don't have enough reputation to affect others.", color=discord.Color.red()))
            return

        # Apply reputation change
        source_user.reputation -= REPUTATION_COST
        target_user.reputation += change
        
        # Update roles based on new reputation
        guild = interaction.guild
        for role_name, threshold in ROLE_THRESHOLDS.items():
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                if target_user.reputation >= threshold and role not in user.roles:
                    await user.add_roles(role)
                    logger.info(f"Added role {role_name} to {user.name}")
                elif target_user.reputation < threshold and role in user.roles:
                    await user.remove_roles(role)
                    logger.info(f"Removed role {role_name} from {user.name}")

        # Log change
        db.add(ReputationChange(source_user_id=interaction.user.id, target_user_id=user.id, change=change))

        db.commit()
        embed = Embed(title="Reputation Update", description=f"{user.name}'s reputation is now {target_user.reputation:.2f}.", color=discord.Color.green())
        embed.add_field(name="Cost", value=f"Your reputation was decreased by {REPUTATION_COST} to perform this action.")
        await interaction.response.send_message(embed=embed)
        logger.info(f"Reputation change: {interaction.user.name} affected {user.name}'s reputation by {change}")

        # Notify the user whose reputation was changed
        if user.id != interaction.user.id:
            try:
                await user.send(embed=Embed(description=f"Your reputation has been changed by {change} by {interaction.user.name}.", color=discord.Color.blue()))
            except discord.errors.Forbidden:
                logger.warning(f"Could not send DM to {user.name}. They might have DMs disabled.")

    except SQLAlchemyError as e:
        logger.error(f"Database Error: {e}")
        await interaction.response.send_message(embed=Embed(description="An error occurred while updating reputation.", color=discord.Color.red()))
    finally:
        db.close()

@client.tree.command(name="check_reputation", description="Check a user's reputation", guild=discord.Object(id=GUILD_ID))
async def check_reputation(interaction: Interaction, user: Optional[Member] = None):
    if user is None:
        user = interaction.user

    db = next(get_db())
    try:
        reputation = db.query(UserReputation).filter_by(user_id=user.id).first()
        if not reputation:
            reputation = UserReputation(user_id=user.id, reputation=0.0)
        
        embed = Embed(title="Reputation Check", description=f"{user.name}'s current reputation is {reputation.reputation:.2f}.", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)
    except SQLAlchemyError as e:
        logger.error(f"Database Error: {e}")
        await interaction.response.send_message(embed=Embed(description="An error occurred while checking reputation.", color=discord.Color.red()))
    finally:
        db.close()

@client.tree.command(name="top_reputations", description="List top reputations in the server", guild=discord.Object(id=GUILD_ID))
async def top_reputations(interaction: Interaction, count: int = 5):
    if count < 1 or count > 20:
        await interaction.response.send_message(embed=Embed(description="Please choose a count between 1 and 20.", color=discord.Color.orange()))
        return

    db = next(get_db())
    try:
        top_users = db.query(UserReputation).order_by(UserReputation.reputation.desc()).limit(count).all()
        embed = Embed(title="Top Reputations", color=discord.Color.gold())
        
        for idx, user_rep in enumerate(top_users, 1):
            user = await interaction.guild.fetch_member(user_rep.user_id)
            embed.add_field(name=f"#{idx}: {user.name}", value=f"Reputation: {user_rep.reputation:.2f}", inline=False)
        
        if not top_users:
            embed.description = "No reputation data available yet."
        
        await interaction.response.send_message(embed=embed)
    except SQLAlchemyError as e:
        logger.error(f"Database Error: {e}")
        await interaction.response.send_message(embed=Embed(description="An error occurred while fetching top reputations.", color=discord.Color.red()))
    finally:
        db.close()

@client.tree.command(name="reputation_history", description="View your reputation history", guild=discord.Object(id=GUILD_ID))
async def reputation_history(interaction: Interaction, limit: int = 5):
    if limit < 1 or limit > 20:
        await interaction.response.send_message(embed=Embed(description="Please choose a limit between 1 and 20.", color=discord.Color.orange()))
        return

    db = next(get_db())
    try:
        history = db.query(ReputationChange).filter_by(target_user_id=interaction.user.id).order_by(ReputationChange.timestamp.desc()).limit(limit).all()
        embed = Embed(title=f"Reputation History for {interaction.user.name}", color=discord.Color.blue())
        
        if not history:
            embed.description = "No reputation changes recorded."
        else:
            for change in history:
                source_user = await interaction.guild.fetch_member(change.source_user_id)
                embed.add_field(name=f"Changed by {source_user.name}", value=f"Change: {change.change:.2f} on {change.timestamp.strftime('%Y-%m-%d %H:%M')}", inline=False)
        
        await interaction.response.send_message(embed=embed)
    except SQLAlchemyError as e:
        logger.error(f"Database Error: {e}")
        await interaction.response.send_message(embed=Embed(description="An error occurred while fetching reputation history.", color=discord.Color.red()))
    finally:
        db.close()

@client.tree.command(name="reset_reputations", description="Reset all reputations (Administrator Only)", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_role("Administrator")
async def reset_reputations(interaction: Interaction):
    db = next(get_db())
    try:
        db.query(UserReputation).update({'reputation': STARTING_REPUTATION})
        db.query(ReputationChange).delete()
        db.commit()
        await interaction.response.send_message(embed=Embed(description=f"All reputations have been reset to {STARTING_REPUTATION}.", color=discord.Color.green()))
    except SQLAlchemyError as e:
        logger.error(f"Database Error: {e}")
        await interaction.response.send_message(embed=Embed(description="An error occurred while resetting reputations.", color=discord.Color.red()))
    finally:
        db.close()

@client.tree.command(name="help", description="Get help with bot commands", guild=discord.Object(id=GUILD_ID))
async def help_command(interaction: Interaction):
    embed = Embed(title="Reputation Bot Help", color=discord.Color.blue())
    embed.add_field(name="/reputation <@user> [change]", value=f"Change a user's reputation. Costs you {REPUTATION_COST} reputation to use.", inline=False)
    embed.add_field(name="/check_reputation [@user]", value="Check your or another user's reputation.", inline=False)
    embed.add_field(name="/top_reputations [count]", value="List top reputations in the server. Default count is 5, max is 20.", inline=False)
    embed.add_field(name="/reputation_history [limit]", value="View your recent reputation changes. Default is 5, max is 20.", inline=False)
    embed.add_field(name="/reset_reputations", value="Reset all reputations (Administrator only).", inline=False)
    embed.add_field(name="Cooldown", value=f"There's a {COOLDOWN_HOURS} hour cooldown for changing reputation per user-target pair.", inline=False)
    await interaction.response.send_message(embed=embed)

@client.event
async def on_command_error(interaction: Interaction, error):
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
    elif isinstance(error, (app_commands.errors.MissingRole)):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    else:
        logger.error(f"Command Error: {error}")
        await interaction.response.send_message("An error occurred while executing this command.", ephemeral=True)

# Run the bot
client.run(BOT_TOKEN)