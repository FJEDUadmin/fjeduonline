args <- commandArgs(trailingOnly = TRUE)
cran_list_path <- ifelse(length(args) >= 1, args[1], "r_modules/cran_packages.txt")
bioc_list_path <- ifelse(length(args) >= 2, args[2], "r_modules/bioc_packages.txt")
local_pkg_dir <- ifelse(length(args) >= 3, args[3], "r_modules/packages")

message("R package bootstrap starting...")
message(paste("CRAN list:", cran_list_path))
message(paste("Bioconductor list:", bioc_list_path))
message(paste("Local package dir:", local_pkg_dir))

safe_read_lines <- function(path) {
  if (!file.exists(path)) {
    return(character(0))
  }
  lines <- readLines(path, warn = FALSE, encoding = "UTF-8")
  lines <- trimws(lines)
  lines <- lines[lines != ""]
  lines <- lines[!grepl("^#", lines)]
  return(unique(lines))
}

safe_install_cran <- function(pkg) {
  tryCatch({
    install.packages(pkg, repos = "https://cloud.r-project.org", dependencies = TRUE)
    TRUE
  }, error = function(e) {
    message(paste("WARN: failed to install CRAN package", pkg, ":", e$message))
    FALSE
  })
}

safe_install_bioc <- function(pkg) {
  tryCatch({
    if (!requireNamespace("BiocManager", quietly = TRUE)) {
      install.packages("BiocManager", repos = "https://cloud.r-project.org")
    }
    BiocManager::install(pkg, ask = FALSE, update = FALSE)
    TRUE
  }, error = function(e) {
    message(paste("WARN: failed to install Bioconductor package", pkg, ":", e$message))
    FALSE
  })
}

safe_install_local <- function(tar_path) {
  tryCatch({
    install.packages(tar_path, repos = NULL, type = "source")
    TRUE
  }, error = function(e) {
    message(paste("WARN: failed to install local package", tar_path, ":", e$message))
    FALSE
  })
}

installed <- rownames(installed.packages())

cran_pkgs <- safe_read_lines(cran_list_path)
if (length(cran_pkgs) > 0) {
  for (pkg in cran_pkgs) {
    if (!(pkg %in% installed)) {
      safe_install_cran(pkg)
    }
  }
}

bioc_pkgs <- safe_read_lines(bioc_list_path)
if (length(bioc_pkgs) > 0) {
  for (pkg in bioc_pkgs) {
    if (!(pkg %in% rownames(installed.packages()))) {
      safe_install_bioc(pkg)
    }
  }
}

if (dir.exists(local_pkg_dir)) {
  tarballs <- list.files(local_pkg_dir, pattern = "\\.tar\\.gz$", full.names = TRUE)
  if (length(tarballs) > 0) {
    for (tarball in tarballs) {
      safe_install_local(tarball)
    }
  }
}

message("R package bootstrap completed.")
