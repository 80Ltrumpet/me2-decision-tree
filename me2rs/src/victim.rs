use crate::ally::Ally;

#[derive(Debug)]
pub enum VictimReason {
    ArmorNotUpgraded,
    ShieldNotUpgraded,
    WeaponNotUpgraded,
    NonidealBioticSelected,
}

impl VictimReason {
    /// Returns a single victim from the given `team` based on this reason.
    ///
    /// # Panics
    ///
    /// This method panics if the returned `Ally` would be empty.
    pub fn get_victim(&self, team: Ally) -> Ally {
        let priority = match self {
            Self::ArmorNotUpgraded => Priority::ARMOR_NOT_UPGRADED,
            Self::ShieldNotUpgraded => Priority::SHIELD_NOT_UPGRADED,
            Self::WeaponNotUpgraded => Priority::WEAPON_NOT_UPGRADED,
            Self::NonidealBioticSelected => Priority::NONIDEAL_BIOTIC,
        };
        match priority.filter(team).next() {
            Some(victim) => victim,
            None => {
                panic!("No victim for {:?} given {:?}", team, self);
            }
        }
    }
}

#[cfg(test)]
mod test {
    use super::VictimReason::*;
    use crate::ally::Ally;

    #[test]
    #[should_panic]
    fn get_victim_invalid() {
        // Jack is required to be in the team for this check.
        ArmorNotUpgraded.get_victim(Ally::OPTIONAL);
    }

    #[test]
    fn get_victim_valid() {
        let team = Ally::TALI | Ally::GARRUS | Ally::MIRANDA | Ally::JACK;
        assert_eq!(NonidealBioticSelected.get_victim(team), Ally::JACK);
        assert_eq!(WeaponNotUpgraded.get_victim(team), Ally::GARRUS);
        assert_eq!(ShieldNotUpgraded.get_victim(team), Ally::TALI);
    }
}

/// The `defense` submodule defines functions for computing the number of
/// victims in the defense team.
pub mod defense {
    use super::Priority;
    use crate::ally::Ally;
    use std::ops::BitOr;

    fn base_score_for_ally(ally: Ally) -> u8 {
        match ally {
            Ally::GARRUS | Ally::GRUNT | Ally::ZAEED => 4,
            Ally::JACOB
            | Ally::LEGION
            | Ally::MIRANDA
            | Ally::SAMARA
            | Ally::THANE
            | Ally::MORINTH => 2,
            Ally::JACK | Ally::KASUMI | Ally::MORDIN | Ally::TALI => 1,
            _ => {
                panic!("score_for_ally({:?}, ...) is invalid", ally);
            }
        }
    }

    fn score_for_team(team: Ally, loyal: Ally) -> f32 {
        if team.empty() {
            panic!("score_for_team({:?}, ...) is invalid", team);
        }
        // Disloyal allies' scores are reduced by 1.
        let score_for_ally =
            |ally| base_score_for_ally(ally) - (ally % !loyal) as u8;
        let ally_scores = team.into_iter().map(score_for_ally);
        ally_scores.sum::<u8>() as f32 / team.len() as f32
    }

    fn get_death_toll(team: Ally, loyal: Ally) -> usize {
        let score = score_for_team(team, loyal);
        match team.len() {
            0 => {
                panic!("get_death_toll({:?}, ...) is invalid", team);
            }
            1 => (score < 2.0) as usize,
            2 => match score {
                x if x <= 0.0 => 2,
                x if x < 2.0 => 1,
                _ => 0,
            },
            3 => match score {
                x if x <= 0.0 => 3,
                x if x < 1.0 => 2,
                x if x < 2.0 => 1,
                _ => 0,
            },
            4 => match score {
                x if x <= 0.0 => 4,
                x if x < 0.5 => 3,
                x if x <= 1.0 => 2,
                x if x < 2.0 => 1,
                _ => 0,
            },
            _ => match score {
                x if x < 0.5 => 3,
                x if x < 1.5 => 2,
                x if x < 2.0 => 1,
                _ => 0,
            },
        }
    }

    /// Returns one or more victims from the given `team`, prioritizing allies
    /// who are not `loyal`.
    ///
    /// # Panics
    ///
    /// This method panics if `team` is empty.
    pub fn get_victims(team: Ally, loyal: Ally) -> Ally {
        let toll = get_death_toll(team, loyal);
        let disloyal = Priority::INSUFFICIENT_DEFENSE.filter(team & !loyal);
        let loyal = Priority::INSUFFICIENT_DEFENSE.filter(team & loyal);
        disloyal
            .chain(loyal)
            .take(toll)
            .fold(Ally::NOBODY, Ally::bitor)
    }

    #[cfg(test)]
    mod test {
        use super::*;
        use crate::ally::Ally;

        #[test]
        #[should_panic]
        fn base_score_for_multiple_allies() {
            base_score_for_ally(Ally::IDEAL_LEADERS);
        }

        #[test]
        #[should_panic]
        fn score_for_nobody() {
            score_for_team(Ally::NOBODY, Ally::EVERYONE);
        }

        #[test]
        fn score_for_valid_team() {
            let team = Ally::ZAEED | Ally::JACOB | Ally::KASUMI;
            let loyal = Ally::JACOB | Ally::KASUMI | Ally::MIRANDA;
            assert_eq!(score_for_team(team, loyal), 2.0);
        }

        #[test]
        #[should_panic]
        fn death_toll_for_empty_team() {
            get_death_toll(Ally::NOBODY, Ally::BIOTICS);
        }

        #[test]
        fn death_toll() {
            let team = Ally::MORINTH | Ally::GRUNT | Ally::MORDIN;
            let loyal = Ally::GRUNT | Ally::GARRUS;
            assert_eq!(get_death_toll(team, loyal), 1);
        }

        #[test]
        #[should_panic]
        fn get_victims_invalid() {
            get_victims(Ally::NOBODY, Ally::NOBODY);
        }

        #[test]
        fn get_victims_valid() {
            let team = Ally::MIRANDA | Ally::TALI | Ally::SAMARA;
            let loyal = Ally::TALI | Ally::SAMARA;
            assert_eq!(get_victims(team, loyal), Ally::MIRANDA);
        }
    }
}

/// Defines arrays containing the order in which allies are selected as victims
/// when certain conditions are met.
pub struct Priority {
    slice: &'static [Ally],
}

impl Priority {
    /// Filters the priority list based on the available `team`.
    pub fn filter(&self, team: Ally) -> Box<dyn Iterator<Item = Ally>> {
        Box::new(
            self.slice
                .into_iter()
                .copied()
                .filter(move |&ally| ally % team),
        )
    }

    /// The _Silaris Armor_ ship upgrade was not purchased.
    pub const ARMOR_NOT_UPGRADED: Priority = Priority {
        slice: &[Ally::JACK],
    };

    /// The _Cyclonic Shields_ ship upgrade was not purchased.
    pub const SHIELD_NOT_UPGRADED: Priority = Priority {
        slice: &[
            Ally::KASUMI,
            Ally::LEGION,
            Ally::TALI,
            Ally::THANE,
            Ally::GARRUS,
            Ally::ZAEED,
            Ally::GRUNT,
            Ally::SAMARA,
            Ally::MORINTH,
        ],
    };

    /// The _Thanix Cannon_ ship upgrade was not purchased.
    pub const WEAPON_NOT_UPGRADED: Priority = Priority {
        slice: &[
            Ally::THANE,
            Ally::GARRUS,
            Ally::ZAEED,
            Ally::GRUNT,
            Ally::JACK,
            Ally::SAMARA,
            Ally::MORINTH,
        ],
    };

    /// A disloyal or non-ideal biotic was selected.
    pub const NONIDEAL_BIOTIC: Priority = Priority {
        slice: &[
            Ally::THANE,
            Ally::JACK,
            Ally::GARRUS,
            Ally::LEGION,
            Ally::GRUNT,
            Ally::SAMARA,
            Ally::JACOB,
            Ally::MORDIN,
            Ally::TALI,
            Ally::KASUMI,
            Ally::ZAEED,
            Ally::MORINTH,
        ],
    };

    /// The average defense score of the allies who _hold the line_ during
    /// the final battle was too low.
    pub const INSUFFICIENT_DEFENSE: Priority = Priority {
        slice: &[
            Ally::MORDIN,
            Ally::TALI,
            Ally::KASUMI,
            Ally::JACK,
            Ally::MIRANDA,
            Ally::JACOB,
            Ally::GARRUS,
            Ally::SAMARA,
            Ally::MORINTH,
            Ally::LEGION,
            Ally::THANE,
            Ally::ZAEED,
            Ally::GRUNT,
        ],
    };
}
