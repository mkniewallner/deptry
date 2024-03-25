use ignore::types::{Types, TypesBuilder};
use ignore::{DirEntry, Walk, WalkBuilder};
use path_slash::PathExt;
use pyo3::types::PyList;
use pyo3::{pyfunction, PyObject, PyResult, Python};
use regex::Regex;
use std::path::PathBuf;

#[pyfunction]
#[pyo3(signature = (directories, exclude, extend_exclude, using_default_exclude, ignore_notebooks=false))]
pub fn find_python_files(
    py: Python,
    directories: Vec<PathBuf>,
    exclude: Vec<&str>,
    extend_exclude: Vec<&str>,
    using_default_exclude: bool,
    ignore_notebooks: bool,
) -> PyResult<PyObject> {
    let mut unique_directories = directories;
    unique_directories.dedup();

    let python_files: Vec<_> = build_walker(
        unique_directories,
        [exclude, extend_exclude].concat(),
        using_default_exclude,
        ignore_notebooks,
    )
    .flatten()
    .filter(|entry| entry.path().is_file())
    .map(|entry| {
        entry
            .path()
            .to_string_lossy()
            .strip_prefix("./")
            .unwrap_or(&entry.path().to_string_lossy())
            .to_owned()
    })
    .collect();

    Ok(PyList::new(py, &python_files).into())
}

fn build_walker(
    directories: Vec<PathBuf>,
    excluded_patterns: Vec<&str>,
    use_git_ignore: bool,
    ignore_notebooks: bool,
) -> Walk {
    let (first_directory, additional_directories) = directories.split_first().unwrap();

    let mut walk_builder = WalkBuilder::new(first_directory);
    for path in additional_directories {
        walk_builder.add(path);
    }

    let re: Option<Regex> = if excluded_patterns.is_empty() {
        None
    } else {
        Some(Regex::new(format!(r"^({})", excluded_patterns.join("|")).as_str()).unwrap())
    };

    walk_builder
        .types(build_types(ignore_notebooks).unwrap())
        .hidden(false)
        .git_ignore(use_git_ignore)
        .require_git(false)
        .filter_entry(move |entry| entry_satisfies_predicate(entry, re.as_ref()))
        .build()
}

fn build_types(ignore_notebooks: bool) -> Result<Types, ignore::Error> {
    let mut types_builder = TypesBuilder::new();
    types_builder.add("python", "*.py").unwrap();
    types_builder.select("python");

    if !ignore_notebooks {
        types_builder.add("jupyter", "*.ipynb").unwrap();
        types_builder.select("jupyter");
    }

    types_builder.build()
}

fn entry_satisfies_predicate(entry: &DirEntry, regex: Option<&Regex>) -> bool {
    if regex.is_none() {
        return true;
    }

    let path_str = entry.path().to_slash_lossy();
    !regex
        .unwrap()
        .is_match(path_str.strip_prefix("./").unwrap_or(&path_str).as_ref())
}

#[cfg(test)]
mod tests {
    use super::*;
    use rstest::rstest;
    use std::env;
    use std::path::Path;

    fn get_test_data_directory() -> &'static Path {
        Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/tests/data/file_finder"
        ))
    }

    fn py_object_to_sorted_vec_string(py: Python, py_object: PyObject) -> Vec<String> {
        let mut list: Vec<String> = py_object.extract(py).unwrap();
        list.sort();
        list
    }

    #[test]
    fn test_simple() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            env::set_current_dir(get_test_data_directory()).unwrap();

            let result = find_python_files(
                py,
                vec![PathBuf::from("./")],
                vec![".venv"],
                vec!["other_dir"],
                false,
                false,
            )
            .unwrap();

            assert_eq!(
                py_object_to_sorted_vec_string(py, result),
                vec![
                    ".cache/file1.py",
                    ".cache/file2.py",
                    "another_dir/subdir/file1.py",
                    "dir/subdir/file1.ipynb",
                    "dir/subdir/file1.py",
                    "dir/subdir/file2.py",
                    "dir/subdir/file3.py",
                    "subdir/file1.py",
                ],
            );
        })
    }

    #[test]
    fn test_only_matches_start() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            env::set_current_dir(get_test_data_directory()).unwrap();

            let result = find_python_files(
                py,
                vec![PathBuf::from("./")],
                vec!["foo"],
                vec!["subdir"],
                false,
                false,
            )
            .unwrap();

            assert_eq!(
                py_object_to_sorted_vec_string(py, result),
                vec![
                    ".cache/file1.py",
                    ".cache/file2.py",
                    "another_dir/subdir/file1.py",
                    "dir/subdir/file1.ipynb",
                    "dir/subdir/file1.py",
                    "dir/subdir/file2.py",
                    "dir/subdir/file3.py",
                    "other_dir/subdir/file1.py",
                ],
            );
        })
    }

    #[test]
    fn test_ignores_notebooks() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            env::set_current_dir(get_test_data_directory()).unwrap();

            let result =
                find_python_files(py, vec![PathBuf::from("./")], vec![], vec![], false, true)
                    .unwrap();

            assert_eq!(
                py_object_to_sorted_vec_string(py, result),
                vec![
                    ".cache/file1.py",
                    ".cache/file2.py",
                    "another_dir/subdir/file1.py",
                    "dir/subdir/file1.py",
                    "dir/subdir/file2.py",
                    "dir/subdir/file3.py",
                    "other_dir/subdir/file1.py",
                    "subdir/file1.py",
                ],
            );
        })
    }

    #[rstest]
    #[case(
        vec![".*file1"],
        vec![
            ".cache/file2.py",
            "dir/subdir/file2.py",
            "dir/subdir/file3.py",
        ],
    )]
    #[case(
        vec![".cache|other.*subdir"],
        vec![
            "another_dir/subdir/file1.py",
            "dir/subdir/file1.ipynb",
            "dir/subdir/file1.py",
            "dir/subdir/file2.py",
            "dir/subdir/file3.py",
            "subdir/file1.py",
        ],
    )]
    #[case(
        vec![".*/subdir/"],
        vec![
            ".cache/file1.py",
            ".cache/file2.py",
            "subdir/file1.py",
        ],
    )]
    fn test_regex_argument(#[case] exclude: Vec<&str>, #[case] expected: Vec<&str>) {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            env::set_current_dir(get_test_data_directory()).unwrap();

            let result =
                find_python_files(py, vec![PathBuf::from("./")], exclude, vec![], false, false)
                    .unwrap();

            assert_eq!(py_object_to_sorted_vec_string(py, result), expected);
        })
    }

    #[rstest]
    #[case(
        vec![".*file1"],
        vec![
            "dir/subdir/file2.py",
            "dir/subdir/file3.py",
        ],
    )]
    #[case(
        vec![".*file1|.*file2"],
        vec!["dir/subdir/file3.py"],
    )]
    #[case(
        vec![".*/subdir/"],
        vec![],
    )]
    fn test_multiple_source_directories(#[case] exclude: Vec<&str>, #[case] expected: Vec<&str>) {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            env::set_current_dir(get_test_data_directory()).unwrap();

            let result = find_python_files(
                py,
                vec![PathBuf::from("./dir"), PathBuf::from("./other_dir")],
                exclude,
                vec![],
                false,
                false,
            )
            .unwrap();

            assert_eq!(py_object_to_sorted_vec_string(py, result), expected);
        })
    }

    #[test]
    fn test_duplicates_are_removed() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            env::set_current_dir(get_test_data_directory()).unwrap();

            let result = find_python_files(
                py,
                vec![PathBuf::from("./"), PathBuf::from("./")],
                vec![],
                vec![],
                false,
                false,
            )
            .unwrap();

            assert_eq!(
                py_object_to_sorted_vec_string(py, result),
                vec![
                    ".cache/file1.py",
                    ".cache/file2.py",
                    "another_dir/subdir/file1.py",
                    "dir/subdir/file1.ipynb",
                    "dir/subdir/file1.py",
                    "dir/subdir/file2.py",
                    "dir/subdir/file3.py",
                    "other_dir/subdir/file1.py",
                    "subdir/file1.py",
                ],
            );
        })
    }
}
