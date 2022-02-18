#!/usr/bin/env Rscript
# timing-analysis.R
# simple utility to get some general info about timing results

library(readr)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0) {
	stop("Usage: timing-analysis.R FILE", call. = FALSE)
}
timing_path <- args[1]

col_names <- c("timestamp", "run", "duration")
col_types <- cols(timestamp = col_datetime(format = "%s"),
									run = col_integer(),
									duration = col_time())
df <- read_csv(timing_path, col_names = col_names, col_types = col_types)

print(df)
