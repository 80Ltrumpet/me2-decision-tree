use super::PostIFF;

use crate::ally::Ally;

pub struct Ledger {
    pub cargo: Option<[Ally; 3]>,
    pub walk: Option<[Ally; 3]>,
    pub biotic: Option<Ally>,
    pub escort: Option<Ally>,
    pub final_squad: Option<Ally>,
    pub leaders: Option<Ally>,
    pub loyalty: Option<Ally>,
    pub recruits: Option<Ally>,
    pub second_leader: Option<Ally>,
    pub tech: Option<Ally>,
    pub post_iff: Option<PostIFF>,
    pub rescue: Option<Option<bool>>,
    pub armor: Option<bool>,
    pub first_leader: Option<bool>,
    pub shield: Option<bool>,
    pub weapon: Option<bool>,
}

impl Ledger {
    pub fn new() -> Self {
        Self {
            armor: None,
            biotic: None,
            cargo: None,
            escort: None,
            final_squad: None,
            first_leader: None,
            leaders: None,
            loyalty: None,
            post_iff: None,
            recruits: None,
            rescue: None,
            second_leader: None,
            shield: None,
            tech: None,
            walk: None,
            weapon: None,
        }
    }
}
