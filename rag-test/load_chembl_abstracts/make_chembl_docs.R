library(data.table)
library(stringr)
library(dplyr)

df <- fread("./chembl_studies.csv")

apply(df, 1, function(x){
    
TEXT_TEMPLATE <- paste0("
", x["study_title"], "

a ", tolower(x["study_doctype"]), " by ", x["study_authors"], "

DOI: ", x["study_doi"], "

", x["study_abstract"], "

")

tmp <- file(paste0("./chembl_docs/",  gsub("<", "_",  gsub(">", "_", gsub(";", "_",  gsub(":", "_", gsub("/", "_", gsub(".", "_", gsub("\\s", "_", x["study_doi"]), fixed=TRUE)))))), ".txt"))
writeLines(TEXT_TEMPLATE, tmp)
close(tmp)

})