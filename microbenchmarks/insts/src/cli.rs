#[derive(clap::Parser, Debug)]
pub struct Options {
    /// Set the output file, where the results will be written as JSON.
    /// If not provided, output will be printed to stdout.
    #[clap(short, long, value_parser)]
    pub output: Option<String>,

    /// Which mode to benchmark
    #[clap(short, long, value_parser)]
    pub mode: BenchmarkingMode,

    /// How many iterations to use by default
    #[clap(short, long, value_parser, default_value_t = 1_600_000_000)]
    pub iterations: u64,
}

#[derive(clap::ValueEnum, Copy, Clone, Debug)]
pub enum BenchmarkingMode {
    Mte,
    Pac,
    Cheri,
    Mpk,
    ClockTest,
}
