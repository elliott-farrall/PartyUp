import os

from discord import (
    ApplicationContext, Bot, Colour, Embed, Guild, Member, Role, Status,
    default_permissions,
)
from dotenv import load_dotenv

from src.options import RoleOption, SizeOption
from src.party import Party

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

class PartyUp(Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.init_commands()

    def run(self, token: str) -> None:
        print("[*] Starting bot...")
        super().run(token, reconnect=True)

    async def on_ready(self) -> None:
        print(f"[*] We have logged in as {self.user}")

    async def on_member_update(self, before: Member, after: Member):
        # Remove player from party if they go offline
        if after.status == Status.offline:
            for party in Party.list:
                party.remove(after)

    def get_role(self, ctx: ApplicationContext, role_id: str) -> Role | None:
        if type(ctx.interaction.guild) is Guild:
            role = ctx.interaction.guild.get_role(int(role_id))
            if type(role) is Role:
                return role
            else:
                return None
        else:
            return None

    def init_commands(self) -> None:
        party = self.create_group("party", "Party commands.")

        # ------------------------------- User Commands ------------------------------ #

        @party.command(name="create", description="Create a party for a specific role.")
        async def create(
            ctx: ApplicationContext,
            role_id: RoleOption(), # type: ignore
            size: SizeOption() # type: ignore
        ) -> None:
            role = self.get_role(ctx, role_id)
            if role is None:
                return

            party = Party.get(role)
            if party is None:
                party = Party(ctx.channel, ctx.author, role, size)
                await ctx.respond(
                    f"Party created for {party.role.mention} with size {size}."
                )
            else:
                await ctx.respond(f"Party already exits for {role.name}.")

        @party.command(
            name="adjust", description="Adjust party size for a specific role."
        )
        async def adjust(
            ctx: ApplicationContext,
            role_id: RoleOption(), # type: ignore
            size: SizeOption() # type: ignore
        ) -> None:
            role = self.get_role(ctx, role_id)
            if role is None:
                print("[!] Role not found.")
                return

            party = Party.get(role)
            if party is not None:
                if size >= len(party.players):
                    party.size = size
                    party.refresh()
                    await ctx.respond(
                        f"Party size adjusted for {party.role.mention} to {size}."
                    )
                else:
                    await ctx.respond(
                        f"Cannot adjust party size to {size} as there are already {len(party.players)} players in the party."
                    )
            else:
                await ctx.respond(f"No party for {role.name}.")

        # ------------------------------ Admin Commands ------------------------------ #

        @party.command(name="list", description="List all available parties.")
        @default_permissions(administrator=True)
        async def list(ctx: ApplicationContext) -> None:
            if Party.list:
                embed = Embed(title="Current Parties", color=Colour.blurple())
                for party in Party.list:
                    members_list = "\n".join(
                        f"  - {member.display_name}" for member in party.players
                    )
                    embed.add_field(
                        name=f"{party.role.name} ({len(party.players)}/{party.size})",
                        value=members_list if members_list else "No members",
                        inline=False
                    )
                await ctx.respond(embed=embed)
            else:
                await ctx.respond("No parties available.")

        @party.command(name="kick", description="Kick a member of a party.")
        @default_permissions(administrator=True)
        async def kick(
            ctx: ApplicationContext,
            role_id: RoleOption(), # type: ignore
            member: Member
        ) -> None:
            role = self.get_role(ctx, role_id)
            if role is None:
                print("[!] Role not found.")
                return

            party = Party.get(role)
            if party is not None:
                if member in party.players:
                    party.remove(member)
                    party.refresh()
                    await ctx.respond(
                        f"Kicked {member.mention} from {party.role.mention}."
                    )
                else:
                    await ctx.respond(
                        f"{member.mention} is not in the party for {role.name}."
                    )
            else:
                await ctx.respond(f"No party for {role.name}")

        @party.command(name="remove", description="Remove a party for a specific role.")
        @default_permissions(administrator=True)
        async def remove(
            ctx: ApplicationContext,
            role_id: RoleOption() # type: ignore
        ) -> None:
            role = self.get_role(ctx, role_id)
            if role is None:
                print("[!] Role not found.")
                return

            party = Party.get(role)
            if party is not None:
                party.__del__()
                await ctx.respond(f"Removed party for {party.role.mention}.")
            else:
                await ctx.respond(f"No party for {role.name}.")


def run() -> None:
    if type(TOKEN) is str:
        bot = PartyUp(debug_guilds=[GUILD_ID])
        bot.run(TOKEN)
    else:
        print("[!] Token not found.")

if __name__ == "__main__":
    run()
