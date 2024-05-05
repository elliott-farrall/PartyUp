from typing import List

from asyncio import create_task

from discord import Bot, User, Member, Status, Role, Option, OptionChoice, Embed, Interaction, Colour, TextChannel, ButtonStyle, default_permissions
from discord.ui import View, Button, button
from discord.ext import tasks
from discord.utils import basic_autocomplete
from discord.commands.context import ApplicationContext, AutocompleteContext

import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

GUILD_ID = os.getenv('GUILD_ID')

# ---------------------------------------------------------------------------- #
#                                   Bot Class                                  #
# ---------------------------------------------------------------------------- #

LFG_PREFIX = 'lfg'

class PartyUp(Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__commands__()

        self.parties = {}

    def run(self, token: str) -> None:
        print('[*] Starting bot...')
        super().run(token, reconnect=True)

    async def on_ready(self) -> None:
        print(f'[*] We have logged in as {self.user}')

    async def on_member_update(self, before: Member, after: Member):
        # Remove player from party if they go offline
        if after.status == Status.offline:
            for party in self.parties:
                party.remove(after)

    def __commands__(self) -> None:
        party = self.create_group('party', 'Party commands.')

        # ---------------------------------- Options --------------------------------- #

        def lfg_roles(ctx: AutocompleteContext) -> List[OptionChoice]:
            return [OptionChoice(name=role.name, value=str(role.id)) for role in ctx.interaction.guild.roles if role.name.startswith(LFG_PREFIX)]
        RoleOption = Option(
            str,
            name='role-id',
            description='ID of role of the party you want to create.',
            autocomplete=basic_autocomplete(lfg_roles)
        )
        SizeOption = Option(
            int,
            name='size',
            description='Size of the party you want to create.'
        )

        # ------------------------------- User Commands ------------------------------ #

        @party.command(
            name='create',
            description='Create a party for a specific role.'
        )
        async def create(ctx: ApplicationContext, role_id: RoleOption, size: SizeOption) -> None:
            role = ctx.interaction.guild.get_role(int(role_id))

            party = Party(ctx.channel, ctx.author, role, size)
            if role.name not in self.parties:
                self.parties[role.name] = party
                party.updater.restart()
                await ctx.respond(f'Party created for {party.role.mention} with size {size}')
            else:
                await ctx.respond(f'Party already exits for {role.name}')

        @party.command(
            name='adjust',
            description='Adjust party szie for a specific role.'
        )
        async def adjust(ctx: ApplicationContext, role_id: RoleOption, size: SizeOption) -> None:
            role = ctx.interaction.guild.get_role(int(role_id))

            if role.name in self.parties:
                party = self.parties[role.name]
                if size >= len(party.players):
                    party.size = size
                    party.updater.restart()
                    await ctx.respond(f'Party size adjusted for {party.role.mention} to {size}')
                else:
                    await ctx.respond(f'Cannot adjust party size to {size} as there are already {len(party.players)} players in the party.')
            else:
                await ctx.respond(f'No party for {role.name}')

        # ------------------------------ Admin Commands ------------------------------ #

        @party.command(
            name='list',
            description='List all available parties'
        )
        @default_permissions(administrator=True)
        async def list(ctx: ApplicationContext) -> None:
            if self.parties:
                parties_list = []
                for role_name, party in self.parties.items():
                    # TODO: Use embed to improve formatting
                    members_list = '\n'.join(f'  - {member.display_name}' for member in party.players)
                    parties_list.append(f'{role_name} ({len(party.players)}/{party.size})\n{members_list}')
                await ctx.respond(f'Current parties:\n\n' + '\n\n'.join(parties_list))
            else:
                await ctx.respond('No parties available')

        @party.command(
            name='kick',
            description='Kick a member of a party.'
        )
        @default_permissions(administrator=True)
        async def kick(ctx: ApplicationContext, role_id: RoleOption, member: User) -> None:
            role = ctx.interaction.guild.get_role(int(role_id))

            if role.name in self.parties:
                if member in self.parties[role.name].players:
                    party = self.parties[role.name]
                    party.remove(member)
                    party.updater.restart()
                    if party.is_empty:
                        self.parties.pop(role.name)
                        party.__del__()
                    await ctx.respond(f'Kicked {member.mention} from {party.role.mention}')
                else:
                    await ctx.respond(f'{member.mention} is not in the party for {role.name}')
            else:
                await ctx.respond(f'No party for {role.name}')

        @party.command(
            name='remove',
            description='Remove a party for a specific role.'
        )
        @default_permissions(administrator=True)
        async def remove(ctx: ApplicationContext, role_id: RoleOption) -> None:
            role = ctx.interaction.guild.get_role(int(role_id))

            if role.name in self.parties:
                party = self.parties.pop(role.name)
                party.__del__()
                await ctx.respond(f'Removed party for {party.role.mention}')
            else:
                await ctx.respond(f'No party for {role.name}')

# ---------------------------------------------------------------------------- #
#                                  Party Class                                 #
# ---------------------------------------------------------------------------- #

class Party:
    def __init__(self, channel: TextChannel, creator: User, role: Role, size: int):
        self.creator = creator
        self.channel = channel
        self.category = channel.category

        self.role = role
        self.size = size

        self.players = {creator}

        self.updater.start()

    def __del__(self) -> None:
        self.updater.cancel()
        del self

    @property
    def is_empty(self) -> bool:
        return len(self.players) == 0
    @property
    def is_full(self) -> bool:
        return len(self.players) == self.size

    def add(self, player: User) -> None:
        if not self.is_full:
            self.players.add(player)

    def remove(self, player: User) -> None:
        if player in self.players:
            self.players.remove(player)

    @tasks.loop(minutes=5)
    async def updater(self) -> None:
        if hasattr(self, 'message'):
            await self.message.delete()

        if self.is_empty:
            self.__del__()
        elif not self.is_full:
            self.message = await self.channel.send(embed=self.msg_embed, view=self.msg_view)

    @property
    def msg_embed(self) -> Embed:
        return PartyMsg(self)
    
    @property
    def msg_view(self) -> View:
        return PartyBtn(self)

class PartyMsg(Embed):
    def __init__(self, party: Party) -> None:
        super().__init__(
            title=f'Party for {party.role.name}',
            colour=Colour.blurple()
        )
        self.party = party

        self.add_field(name='Role', value=party.role.mention)
        self.add_field(name='Size', value=f'{len(party.players)}/{party.size}')
        self.add_field(name='Players', value='\n'.join(player.mention for player in party.players), inline=False)

class PartyBtn(View):
    def __init__(self, party: Party) -> None:
        super().__init__()
        self.party = party

    @button(label='Join', style=ButtonStyle.green)
    async def join_button(self, button: Button, interaction: Interaction) -> None:
        if interaction.user not in self.party.players:
            self.party.add(interaction.user)
            await interaction.response.edit_message(content=f'{interaction.user.mention} joined the party!', embed=self.party.msg_embed, view=self.party.msg_view)
        else:
            await interaction.response.edit_message(content=f'{interaction.user.mention} is already in the party!', embed=self.party.msg_embed, view=self.party.msg_view)
            

    @button(label='Leave', style=ButtonStyle.red)
    async def leave_button(self, button: Button, interaction: Interaction) -> None:
        if interaction.user in self.party.players:
            self.party.remove(interaction.user)
            await interaction.response.edit_message(content=f'{interaction.user.mention} left the party!', embed=self.party.msg_embed, view=self.party.msg_view)
        else:
            await interaction.response.edit_message(content=f'{interaction.user.mention} is not in the party!', embed=self.party.msg_embed, view=self.party.msg_view)         

# ---------------------------------------------------------------------------- #
#                                     Init                                     #
# ---------------------------------------------------------------------------- #

bot = PartyUp(debug_guilds=[GUILD_ID])
bot.run(TOKEN)