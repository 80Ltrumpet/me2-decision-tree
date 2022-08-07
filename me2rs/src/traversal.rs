mod ledger;
mod post_iff;

use crate::ally::Ally;
use ledger::Ledger;
pub use post_iff::PostIFF;

pub struct Traversal<'a> {
    pub cargo: &'a [Ally; 3],
    pub walk: &'a [Ally; 3],
    pub biotic: Ally,
    pub escort: Ally,
    pub final_squad: Ally,
    pub leaders: Ally,
    pub loyalty: Ally,
    pub recruits: Ally,
    pub second_leader: Ally,
    pub spared: Ally, // So much seems off...
    pub tech: Ally,
    pub post_iff: PostIFF,
    pub rescue: Option<bool>,
    pub armor: bool,
    pub first_leader: bool,
    pub shield: bool,
    pub weapon: bool,
}

impl<'a> Traversal<'a> {
    pub fn from_ledger(ledger: &'a Ledger) -> Self {
        Self {
            cargo: ledger.cargo.as_ref().unwrap(),
            walk: ledger.walk.as_ref().unwrap(),
            biotic: ledger.biotic.unwrap(),
            escort: ledger.escort.unwrap(),
            final_squad: ledger.final_squad.unwrap(),
            leaders: ledger.leaders.unwrap(),
            loyalty: ledger.loyalty.unwrap(),
            recruits: ledger.recruits.unwrap(),
            second_leader: ledger.second_leader.unwrap(),
            spared: Ally::NOBODY, // TODO: This is wrong.
            tech: ledger.tech.unwrap(),
            post_iff: ledger.post_iff.unwrap(),
            rescue: ledger.rescue.as_ref().unwrap().clone(),
            armor: ledger.armor.unwrap(),
            first_leader: ledger.first_leader.unwrap(),
            shield: ledger.shield.unwrap(),
            weapon: ledger.weapon.unwrap(),
        }
    }
}

struct TraversalGenerator {
    ledger: Ledger,
    stack: Vec<Ally>,
}

impl TraversalGenerator {
    pub fn new() -> Self {
        Self {
            ledger: Ledger::new(),
            stack: Vec::with_capacity(16),
        }
    }

    pub fn generate(&mut self) -> Option<Traversal> {
        None
    }
}

enum Decision {
    Initial,
    Recruitment,
    LoyaltyMissions,
    Morinth,
    UpgradeArmor,
    UpgradeShield,
    SelectCargoBaySquad,
    UpgradeWeapon,
    TechSpecialist,
    FirstLeader,
    BioticSpecialist,
    SecondLeader,
    RescueTheCrew,
    SelectTheLongWalkSquad,
    SelectFinalSquad,
    PostIFFMissions,
}
