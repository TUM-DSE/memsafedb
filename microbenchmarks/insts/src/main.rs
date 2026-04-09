use crate::benches::run_benchmark;
use crate::cli::Options;
use clap::Parser;
use tracing::info;

mod benches;
mod cli;
mod logging;

fn main() -> anyhow::Result<()> {
    logging::init();

    let options = Options::parse();

    info!("{:?}", options);

    run_benchmark(options)
}

#[cfg(test)]
mod tests {
    #[test]
    fn dummy_test() {
        assert_eq!(2 + 2, 4);
    }
}
