from typing import List

from discord import AutocompleteContext,Guild, Option, OptionChoice
from discord.utils import basic_autocomplete

LFG_PREFIX = "lfg"

def lfg_roles(ctx: AutocompleteContext) -> List[OptionChoice]:
    if type(ctx.interaction.guild) is Guild:
        return [
            OptionChoice(name=role.name, value=str(role.id))
            for role in ctx.interaction.guild.roles
            if role.name.startswith(LFG_PREFIX)
        ]
    return []

class RoleOption(Option):
    def __init__(self):
        super().__init__(
            str,
            name="role",
            description="ID of role of the party you want to create.",
            autocomplete=basic_autocomplete(lfg_roles),
        )

class SizeOption(Option):
    def __init__(self):
        super().__init__(
            int, name="size", description="Size of the party you want to create."
        )
