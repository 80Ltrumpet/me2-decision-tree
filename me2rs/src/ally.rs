use std::{
    iter::Map,
    ops::{BitAnd, BitAndAssign, BitOr, BitOrAssign, Not, Rem},
};

use crate::bits;

/// Wrapper class for Mass Effect 2 ally bitsets
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub struct Ally(u16);

impl Ally {
    // Required Allies
    // Garrus, Jacob, and Miranda are also ideal leaders, so they are grouped
    // together for optimization.
    pub const GARRUS: Ally = Ally(0x0001);
    pub const JACOB: Ally = Ally(0x0002);
    pub const MIRANDA: Ally = Ally(0x0004);
    pub const JACK: Ally = Ally(0x0008);
    pub const MORDIN: Ally = Ally(0x0010);

    // Optional Allies
    pub const GRUNT: Ally = Ally(0x0020);
    pub const KASUMI: Ally = Ally(0x0040);
    pub const LEGION: Ally = Ally(0x0080);
    pub const SAMARA: Ally = Ally(0x0100);
    pub const TALI: Ally = Ally(0x0200);
    pub const THANE: Ally = Ally(0x0400);
    pub const ZAEED: Ally = Ally(0x0800);

    // Morinth is always loyal, so her bit can be ignored regarding loyalty.
    pub const MORINTH: Ally = Ally(0x1000);

    //
    // Groups and Aliases
    //
    pub const NOBODY: Ally = Ally(0);
    pub const EVERYONE: Ally = Ally(0x1fff);

    /// Allies required to complete Mass Effect 2
    pub const REQUIRED: Ally = Ally(
        Self::GARRUS.0
            | Self::JACK.0
            | Self::JACOB.0
            | Self::MIRANDA.0
            | Self::MORDIN.0,
    );

    /// At least three optional allies must be recruited to complete Mass
    /// Effect 2.
    pub const OPTIONAL: Ally = Ally(Self::EVERYONE.0 & !Self::REQUIRED.0);

    /// Optional allies who are directly recruitable
    ///
    /// Morinth is the only ally who is not directly recruitable. If she is in
    /// your crew, she replaced Samara.
    pub const RECRUITABLE: Ally = Ally(Self::OPTIONAL.0 & !Self::MORINTH.0);

    /// Allies who may be disloyal
    pub const LOYALTY: Ally = Ally(Self::EVERYONE.0 & !Self::MORINTH.0);

    /// Allies who are considered ideal leaders
    ///
    /// If any ally represented in this set is loyal and selected as a leader
    /// in the final mission, a death may be avoided. See also `IDEAL_TECHS`
    /// and `IMMORTAL_LEADERS`.
    pub const IDEAL_LEADERS: Ally =
        Ally(Self::GARRUS.0 | Self::JACOB.0 | Self::MIRANDA.0);

    /// Allies who are considered ideal tech specialists
    ///
    /// If any ally represented in this set is loyal and selected as a tech
    /// specialist in the final mission, their death will be avoided if a
    /// loyal leader is selected from `IDEAL_LEADERS` for the first fireteam.
    pub const IDEAL_TECHS: Ally =
        Ally(Self::KASUMI.0 | Self::LEGION.0 | Self::TALI.0);

    /// Allies who are considered ideal biotic specialists
    ///
    /// If any ally represented in this set is loyal and selected as a biotic
    /// specialist in the final mission, the death of an ally will be avoided.
    pub const IDEAL_BIOTICS: Ally =
        Ally(Self::JACK.0 | Self::SAMARA.0 | Self::MORINTH.0);

    /// Allies who can be selected as a tech specialist
    pub const TECHS: Ally = Ally(
        Self::IDEAL_TECHS.0
            | Self::GARRUS.0
            | Self::JACOB.0
            | Self::MORDIN.0
            | Self::THANE.0,
    );

    /// Allies who can be selected as a biotic specialist
    pub const BIOTICS: Ally = Ally(
        Self::IDEAL_BIOTICS.0 | Self::JACOB.0 | Self::MIRANDA.0 | Self::THANE.0,
    );

    /// Allies who can be selected to escort the crew of the Normandy SR2
    pub const ESCORTS: Ally = Ally(Self::EVERYONE.0 & !Self::MIRANDA.0);

    /// Allies who will _not_ die if selected to lead the second fireteam
    /// regardless of loyalty
    pub const IMMORTAL_LEADERS: Ally = Self::MIRANDA;

    fn name(self) -> &'static str {
        match self {
            Self::GARRUS => "Garrus",
            Self::JACOB => "Jacob",
            Self::MIRANDA => "Miranda",
            Self::JACK => "Jack",
            Self::MORDIN => "Mordin",
            Self::GRUNT => "Grunt",
            Self::KASUMI => "Kasumi",
            Self::LEGION => "Legion",
            Self::SAMARA => "Samara",
            Self::TALI => "Tali",
            Self::THANE => "Thane",
            Self::ZAEED => "Zaeed",
            _ => {
                panic!("{:?}.name() is invalid", self);
            }
        }
    }

    /// Determines the number of represented allies.
    pub fn len(self) -> u32 {
        self.0.count_ones()
    }

    /// Returns true if there are no represented allies.
    pub fn empty(self) -> bool {
        self.0 == 0
    }

    /// Produces a list of names as a single `String` for all represented
    /// allies joined with an optional conjunction, if applicable.
    ///
    /// # Examples
    ///
    /// ```
    /// use me2::ally::Ally;
    /// assert_eq!(Ally::NOBODY.names(None), "nobody");
    /// assert_eq!(Ally::GARRUS.names(None), "Garrus");
    /// let team = Ally::GARRUS | Ally::TALI;
    /// assert_eq!(team.names(Some("and")), "Garrus and Tali");
    /// let team = team | Ally::MORDIN;
    /// assert_eq!(team.names(Some("or")), "Garrus, Mordin, or Tali");
    /// ```
    pub fn names(self, conj: Option<&str>) -> String {
        match self.len() {
            0 => String::from("nobody"),
            1 => String::from(self.name()),
            len => {
                let mut names: Vec<&str> =
                    self.into_iter().map(Self::name).collect();
                let conj = format!(" {} ", conj.unwrap_or("and"));
                if len == 2 {
                    names.join(&conj)
                } else {
                    let last = names.pop().unwrap();
                    let mut names = names.join(", ");
                    names.push(',');
                    names.push_str(&conj);
                    names.push_str(&last);
                    names
                }
            }
        }
    }
}

impl From<u16> for Ally {
    fn from(value: u16) -> Self {
        Self(value & Self::EVERYONE.0)
    }
}

impl From<Ally> for u16 {
    fn from(ally: Ally) -> Self {
        ally.0
    }
}

impl From<u32> for Ally {
    fn from(value: u32) -> Self {
        Self((value as u16) & Self::EVERYONE.0)
    }
}

impl From<Ally> for u32 {
    fn from(ally: Ally) -> Self {
        ally.0 as u32
    }
}

impl IntoIterator for Ally {
    type Item = Self;
    type IntoIter = Map<bits::BitValueIterator<u16>, fn(u16) -> Self>;
    fn into_iter(self) -> Self::IntoIter {
        bits::bits(self.0).map(Self)
    }
}

impl BitAnd for Ally {
    type Output = Self;
    fn bitand(self, rhs: Self) -> Self::Output {
        Self(self.0 & rhs.0)
    }
}

impl BitAndAssign for Ally {
    fn bitand_assign(&mut self, rhs: Self) {
        self.0 &= rhs.0;
    }
}

impl BitOr for Ally {
    type Output = Self;
    fn bitor(self, rhs: Self) -> Self::Output {
        Self(self.0 | rhs.0)
    }
}

impl BitOrAssign for Ally {
    fn bitor_assign(&mut self, rhs: Self) {
        self.0 |= rhs.0;
    }
}

impl Not for Ally {
    type Output = Self;
    fn not(self) -> Self::Output {
        Self(!self.0 & Self::EVERYONE.0)
    }
}

/// The remainder operator is overloaded to convert the result of a bitwise
/// AND (`&`) into a `bool` without the otherwise awkward
/// `!(lhs & rhs).empty()` construct.
impl Rem for Ally {
    type Output = bool;
    fn rem(self, rhs: Self) -> Self::Output {
        (self.0 & rhs.0) != 0
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn names() {
        assert_eq!(Ally::NOBODY.names(None), "nobody");
        let mut team = Ally::GRUNT;
        assert_eq!(team.names(Some("!")), "Grunt");
        team |= Ally::LEGION;
        assert_eq!(team.names(None), "Grunt and Legion");
        team |= Ally::JACOB;
        assert_eq!(team.names(Some("or")), "Jacob, Grunt, or Legion");
    }

    #[test]
    fn into_iter() {
        let team = Ally::ZAEED | Ally::TALI | Ally::JACK | Ally::JACOB;
        let mut iter = team.into_iter();
        assert_eq!(iter.next(), Some(Ally::JACOB));
        assert_eq!(iter.next(), Some(Ally::JACK));
        assert_eq!(iter.next(), Some(Ally::TALI));
        assert_eq!(iter.next(), Some(Ally::ZAEED));
        assert_eq!(iter.next(), None);
    }

    #[test]
    fn rem() {
        assert_eq!(Ally::MIRANDA % Ally::REQUIRED, true);
        assert_eq!(Ally::KASUMI % Ally::TECHS, true);
        assert_eq!(Ally::SAMARA % Ally::IDEAL_LEADERS, false);
    }
}
