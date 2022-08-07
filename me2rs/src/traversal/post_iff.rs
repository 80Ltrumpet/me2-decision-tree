use std::iter::FusedIterator;

#[derive(Clone, Copy)]
pub enum PostIFF {
    Zero,
    Few,
    TooMany,
}

impl PostIFF {
    pub fn iter() -> PostIFFIterator {
        PostIFFIterator::new()
    }
}

pub struct PostIFFIterator {
    next: Option<PostIFF>,
    done: bool,
}

impl PostIFFIterator {
    pub fn new() -> Self {
        Self {
            next: None,
            done: false,
        }
    }
}

impl Iterator for PostIFFIterator {
    type Item = PostIFF;
    fn next(&mut self) -> Option<Self::Item> {
        if self.done {
            return None;
        }
        let result = self.next.clone();
        self.next = match result {
            None => Some(PostIFF::Zero),
            Some(PostIFF::Zero) => Some(PostIFF::Few),
            Some(PostIFF::Few) => Some(PostIFF::TooMany),
            _ => {
                self.done = true;
                None
            }
        };
        result
    }
}

impl FusedIterator for PostIFFIterator {}
