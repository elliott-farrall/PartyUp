import os
from typing import List

from discord import (
    Bot, Member, Option, OptionChoice, Status, User, default_permissions,
)
from discord.commands.context import ApplicationContext, AutocompleteContext
from discord.utils import basic_autocomplete
from dotenv import load_dotenv

from .party import Party

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

LFG_PREFIX = "lfg"


class PartyUp(Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__commands__()

        self.parties = {}

    def run(self, token: str) -> None:
        print("[*] Starting bot...")
        super().run(token, reconnect=True)

    async def on_ready(self) -> None:
        print(f"[*] We have logged in as {self.user}")

    async def on_member_update(self, before: Member, after: Member):
        # Remove player from party if they go offline
        if after.status == Status.offline:
            for party in self.parties:
                party.remove(after)

    def __commands__(self) -> None:
        party = self.create_group("party", "Party commands.")

        # ---------------------------------- Options --------------------------------- #

        def lfg_roles(ctx: AutocompleteContext) -> List[OptionChoice]:
            return [
                OptionChoice(name=role.name, value=str(role.id))
                for role in ctx.interaction.guild.roles
                if role.name.startswith(LFG_PREFIX)
            ]

        RoleOption = Option(
            str,
            name="role-id",
            description="ID of role of the party you want to create.",
            autocomplete=basic_autocomplete(lfg_roles),
        )
        SizeOption = Option(
            int, name="size", description="Size of the party you want to create."
        )

        # ------------------------------- User Commands ------------------------------ #

        @party.command(name="create", description="Create a party for a specific role.")
        async def create(
            ctx: ApplicationContext, role_id: RoleOption, size: SizeOption
        ) -> None:
            role = ctx.interaction.guild.get_role(int(role_id))

            party = Party(ctx.channel, ctx.author, role, size)
            if role.name not in self.parties:
                self.parties[role.name] = party
                party.updater.restart()
                await ctx.respond(
                    f"Party created for {party.role.mention} with size {size}"
                )
            else:
                await ctx.respond(f"Party already exits for {role.name}")

        @party.command(
            name="adjust", description="Adjust party size for a specific role."
        )
        async def adjust(
            ctx: ApplicationContext, role_id: RoleOption, size: SizeOption
        ) -> None:
            role = ctx.interaction.guild.get_role(int(role_id))

            if role.name in self.parties:
                party = self.parties[role.name]
                if size >= len(party.players):
                    party.size = size
                    party.updater.restart()
                    await ctx.respond(
                        f"Party size adjusted for {party.role.mention} to {size}"
                    )
                else:
                    await ctx.respond(
                        f"Cannot adjust party size to {size} as there are already {len(party.players)} players in the party."
                    )
            else:
                await ctx.respond(f"No party for {role.name}")

        # ------------------------------ Admin Commands ------------------------------ #

        @party.command(name="list", description="List all available parties")
        @default_permissions(administrator=True)
        async def list(ctx: ApplicationContext) -> None:
            if self.parties:
                parties_list = []
                for role_name, party in self.parties.items():
                    # TODO: Use embed to improve formatting
                    members_list = "\n".join(
                        f"  - {member.display_name}" for member in party.players
                    )
                    parties_list.append(
                        f"{role_name} ({len(party.players)}/{party.size})\n{members_list}"
                    )
                await ctx.respond("Current parties:\n\n" + "\n\n".join(parties_list))
            else:
                await ctx.respond("No parties available")

        @party.command(name="kick", description="Kick a member of a party.")
        @default_permissions(administrator=True)
        async def kick(
            ctx: ApplicationContext, role_id: RoleOption, member: User
        ) -> None:
            role = ctx.interaction.guild.get_role(int(role_id))

            if role.name in self.parties:
                if member in self.parties[role.name].players:
                    party = self.parties[role.name]
                    party.remove(member)
                    party.updater.restart()
                    if party.is_empty:
                        self.parties.pop(role.name)
                        party.__del__()
                    await ctx.respond(
                        f"Kicked {member.mention} from {party.role.mention}"
                    )
                else:
                    await ctx.respond(
                        f"{member.mention} is not in the party for {role.name}"
                    )
            else:
                await ctx.respond(f"No party for {role.name}")

        @party.command(name="remove", description="Remove a party for a specific role.")
        @default_permissions(administrator=True)
        async def remove(ctx: ApplicationContext, role_id: RoleOption) -> None:
            role = ctx.interaction.guild.get_role(int(role_id))

            if role.name in self.parties:
                party = self.parties.pop(role.name)
                party.__del__()
                await ctx.respond(f"Removed party for {party.role.mention}")
            else:
                await ctx.respond(f"No party for {role.name}")


def run() -> None:
    bot = PartyUp(debug_guilds=[GUILD_ID])
    bot.run(TOKEN)


if __name__ == "__main__":
    run()
