# UniBot

A modular Discord bot designed to manage university courses, synchronize Discord channels with academic structures, automate semester transitions, provide interactive reaction roles, and coordinate daily Mensa (cafeteria) visits.

## Features

* **Course Synchronization (`!setlink`)**: Automatically syncs Discord channel names, role names, role colors, and topics (including OLAT/KIS links) with a persistent JSON state (`data/structure.json`). Runs daily and on startup to protect against manual, conflicting changes.
* **Semester Category Cycling (`!cycle`)**: Automatically shifts course channels between "active semester" and "inactive semester" categories. Triggered automatically on the first Monday of a new semester (configurable in JSON), or manually via commands.
* **Interactive Reaction Roles (`!rr`)**: Dynamically generates categorized reaction-role menus based on the academic curriculum structure. Features interactive setup prompts for missing emojis, groups options by subject area, and handles assigning/removing user roles seamlessly.
* **Mensa Schedule Coordination**: A daily resetting schedule (e.g. resets at 14:00) that allows users to react to time slots (11:30, 11:45, etc.) to coordinate lunch groups. Maintains a live-updating list of users alongside a centralized reaction embed.
* **Custom Help System (`!help`)**: Deeply customized, embed-based dynamic help menu detailing categories, specific command usage, and syntax aliases.

## Setup & Deployment (Docker)

This bot is configured to run effortlessly out-of-the-box using Docker and Docker Compose, natively supporting architectures like the Raspberry Pi (ARM). 

### Configuration
1. Clone the repository to your host machine.
2. Create a `.env` file in the root directory and add your bot token:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   ```
3. Ensure your initial JSON state configurations (`structure.json` and `mensa.json`) are located properly in the `data/` directory.

### Starting the Bot

To build the image and start the bot as a persistent background service, run:

```bash
docker compose up -d --build
```
*(Note: If you are using an older installation, you may need to use `docker-compose` instead of `docker compose`)*

The local `data/` folder is explicitly mounted as a volume. This guarantees any edits the bot makes (saving newly selected emojis, capturing Discord role color shifts, Mensa slots, etc.) are safely preserved on your host machine's drive, surviving reboots.

### Updating the Bot

When new features or fixes are pushed to the repository, updating the live container takes just two commands.

1. Pull the latest code from GitHub:
   ```bash
   git pull
   ```
2. Rebuild and restart the container in the background:
   ```bash
   docker compose up -d --build
   ```
Because of the volume binding, your exact `structure.json` environment rules remain untouched while the Python code gracefully updates!
