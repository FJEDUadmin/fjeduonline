args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript adductomics_stats.R <input_json> <output_report>")
}

input_json <- args[1]
output_report <- args[2]

if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("Package 'jsonlite' is required. Install with install.packages('jsonlite').")
}

payload <- jsonlite::fromJSON(input_json, simplifyVector = TRUE)

sample_id <- payload$sample_id
report_title <- payload$report_title
candidates <- payload$candidates
pathways <- payload$pathway_scores

candidate_count <- if (is.null(candidates)) 0 else nrow(as.data.frame(candidates))
pathway_count <- if (is.null(pathways)) 0 else nrow(as.data.frame(pathways))
mean_conf <- if (candidate_count > 0) mean(as.numeric(candidates$confidence_score), na.rm = TRUE) else NA

lines <- c(
  report_title,
  "========================================",
  paste("Sample ID:", sample_id),
  paste("Candidate count:", candidate_count),
  paste("Pathway count:", pathway_count),
  paste("Mean confidence:", ifelse(is.na(mean_conf), "NA", sprintf("%.4f", mean_conf))),
  paste("Generated at:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"))
)

writeLines(lines, con = output_report)
cat(paste("R report generated at", output_report))
