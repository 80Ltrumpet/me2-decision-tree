use crate::ally::Ally;

pub struct Outcome {
    spared: Ally,
    loyal: Ally,
    crew_survival: CrewSurvival,
}

pub enum CrewSurvival {
    None,
    Chakwas,
    Half,
    All,
}

impl Outcome {
    pub fn new(spared: Ally, loyal: Ally, crew_survival: CrewSurvival) -> Self {
        Self {
            spared,
            loyal,
            crew_survival,
        }
    }
}
