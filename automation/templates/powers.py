from typing import Union
from operator import attrgetter
from .yaml_spec import YamlSpec
from ..utils import (
    # logger,
    list_to_or,
    make_bullet,
    make_header,
    ensure_list,
    sort_dict,
    flatten_embedded,
)
from dataclasses import dataclass, field, fields


list_power_types = ["Passive", "Vulny", "Major", "Minor", "Adversary", "Free", "House"]


class Powers(YamlSpec):
    """Set of DofA powers

    Attributes:
        content (dict): input powers converted to human-readable mechanics
        categories (set): set of tuples - set((categ, subcat, subsubcat),(categ2))
    """

    def __init__(self, input_files="04_Powers_SAMPLE.yaml", limit_types: list = None):
        """Initialize. Load file, establish attributes

        Args:
            input_files (str, optional): String to local file or list of strings.
                Defaults to "04_Powers_SAMPLE.yaml".
            limit_types (list, optional): Only output items of provided types.
                Defaults to None, which means all of the following:
                ["Major", "Minor", "Passive", "Adversary", "House", "Vulny"]

        Attributes:
            _data (dict): raw input data
            _categories (set): all power categories
            _template (dict): Template item from input data
            _content (dict): data restructured to sentences.
            _stem (str): Input file name no extension
            _name (str): Last string of stem when split by `_`
            _limit_types (list): See arg above
        """
        input_files = ensure_list(ambiguous_item=input_files)
        super().__init__(
            input_files=[
                file for file in input_files if "Power" in file or "Vuln" in file
            ]
        )
        self._limit_types = limit_types or list_power_types
        self._content = {}
        self._as_list = []

    def sort_template(self, power_dict):
        """Given a power, return OrderedDict in markdown read order"""
        if "Prereq" in power_dict:
            power_dict["Prereq"] = sort_dict(
                power_dict["Prereq"], ["Role", "Level", "Skill", "Power"]
            )
        if "Save" in power_dict:
            power_dict["Save"] = sort_dict(
                power_dict["Save"], ["Trigger", "DR", "Type", "Fail", "Succeed"]
            )

        return sort_dict(
            power_dict,
            [
                "Type",
                "Category",
                "Description",
                "Mechanic",
                "XP",
                "PP",
                "Prereq",
                "Prereq_Role",
                "Prereq_Level",
                "Prereq_Skill",
                "Prereq_Power",
                "To Hit",
                "Damage",
                "Range",
                "AOE",
                "Target",
                "Save",
                "Tags",
            ],
        )

    def save_check_to_txt(self, save: dict) -> str:
        """Given a Save dict from a power, return a readable sentence

        Args:
            save (dict): subset of power dict, save with trigger, DR, type, etc

        Returns:
            save_string (str): readable sentence detailing all features of a save
        """
        sentence = save["Trigger"] + ", target(s) make a "
        sentence += "DR " + str(save["DR"]) + " " if "DR" in save else ""
        sentence += list_to_or(save["Type"]) + " Save"
        output = [sentence, "On fail, target(s) " + save["Fail"]]
        output.append(
            "On success, target(s) " + save["Succeed"]
        ) if "Succeed" in save else None
        return ". ".join(output)

    def merge_mechanics(self, power):
        """Given power dict, merge all appropriate items into Mechanic

        Args:
            power (dict): individual power

        Returns:
            power_merged (dict): power with all mechanic items combined.
        """  # TODO: Add options. Separate func?
        if isinstance(power["Mechanic"], list):  # when mech are list, indent after 1st
            mech_bullets = power["Mechanic"][0] + "\n"
            for mech_bullet in power["Mechanic"][1:]:
                mech_bullets += make_bullet(mech_bullet)
            power["Mechanic"] = mech_bullets[:-1]  # remove last space
        mechanic = (
            ("For " + list_to_or(power["PP"]) + " PP, " + power["Mechanic"] + ". ")
            if "PP" in power
            else power["Mechanic"]
        )
        if "Save" in power:
            mechanic += self.save_check_to_txt(power["Save"]) + ". "
        power["Mechanic"] = "".join([power["Type"], ". ", mechanic])
        power["Category"] = ensure_list(power["Category"])
        power.pop("Save", None)
        return power

    @property
    def as_list(self):
        if not self._as_list:
            self._as_list = [
                Power(Name=k, **v)
                for k, v in self._raw_data.items()
                if v.get("Type", None) in self._limit_types
            ]

    @property
    def content(self) -> dict:
        """Return readable dict with Mechanics collapsed."""
        if not self._content:
            self._content = {
                k: Power(Name=k, **v)
                for k, v in self._raw_data.items()
                if v.get("Type", None) in self._limit_types
            }
        return self._content

    @property
    def categories(self):
        """Return set of tuples: (categories, subcategories)"""
        if not self._categories:
            for v in self._raw_data.values():  # get set of sub/categories for TOC later
                self._categories.add(tuple(ensure_list(v["Category"])))
        return sorted(self._categories)


@dataclass(order=True)
class StatOverride:
    Stat: str
    Value: int

    @property
    def text(self) -> str:
        return f"Set {self.Stat} to {self.Value}"


@dataclass(order=True)
class Prereq:
    Role: str = None
    Level: int = None
    Skill: str = None
    Power: str = None

    @property
    def flat(self) -> dict:
        return flatten_embedded(dict(Prereq=self.__dict__))


@dataclass(order=True)
class Save:
    Trigger: str
    Type: str
    Fail: str
    DR: int = 3
    Succeed: str = None

    @property
    def text(self) -> str:
        """Given a Save dict from a power, return a readable sentence

        Returns:
            save_string (str): readable sentence detailing all features of a save
        """
        sentence = self.Trigger + ", target(s) make a "
        sentence += "DR " + str(self.DR) + " " if self.DR else ""
        sentence += list_to_or(self.Type) + " Save"
        output = [sentence, "On fail, target(s) " + self.Fail]
        output.append("On success, target(s) " + self.Succeed) if self.Succeed else None
        return ". ".join(output)


@dataclass(order=True)
class Power:
    sort_index: str = field(init=False, repr=False)
    Name: str
    Description: str
    Mechanic: Union[str, list] = field(repr=False)
    Merged_Mechanic: str = field(init=False)
    Type: str = field(repr=False)
    Category: Union[str, list] = field(repr=False)
    XP: int = 1
    PP: int = 1
    Range: int = 6
    AOE: str = None
    Target: int = 1
    Options: str = field(default=None, repr=False)
    Choice: str = field(default=None, repr=False)
    Damage: int = 1
    ToHit: int = 1
    Save: dict = field(default=None, repr=False)
    Prereq: dict = field(default=None, repr=False)
    StatOverride: dict = field(default=None, repr=False)
    Tags: list = None

    def __post_init__(self):
        self.sort_index = self.Type
        self.Category = ensure_list(self.Category)
        self.Save = Save(**self.Save) if self.Save else None
        self.Prereq = Prereq(**self.Prereq) if self.Prereq else None
        self.StatOverride = (
            StatOverride(self.StatOverride) if self.StatOverride else None
        )
        self.Merged_Mechanic = self.merge_mechanic()

    def set_choice(self, choice: str):
        self.Choice = choice

    def merge_mechanic(self):
        """Given power dict, merge all appropriate items into Mechanic

        Returns:
            power_merged (dict): power with all mechanic items combined.
        """
        output = []
        if isinstance(self.Mechanic, list):  # when mech are list, indent after 1st
            mech_bullets = self.Mechanic[0] + "\n"
            for mech_bullet in self.Mechanic[1:]:
                mech_bullets += make_bullet(mech_bullet)
            output = mech_bullets[:-1]  # remove last space
        if self.PP:
            output.append("For " + list_to_or(self.PP) + " PP, " + self.Mechanic)
        if self.Save:
            output.append(self.Save.text)
        if self.StatOverride:
            output.append(self.StatOverride)
        return ". ".join([self.Type, *ensure_list(output)])

    def markdown(self, level=2):
        output = make_header(self.Name, level=level) + "\n"
        for f in fields(self):
            if attrgetter(f.name)(self) != f.default and f.repr:
                output += make_bullet(f"{f.name}: {attrgetter(f.name)(self)}")
        return output

    def __repr__(self):
        nodef_f_vals = (
            (f.name, attrgetter(f.name)(self))
            for f in fields(self)
            if attrgetter(f.name)(self) != f.default and f.repr
        )
        # import pdb

        # pdb.set_trace()
        nodef_f_repr = "\n".join(f"{name}={value}" for name, value in nodef_f_vals)
        return f"{self.__class__.__name__}({nodef_f_repr})"
