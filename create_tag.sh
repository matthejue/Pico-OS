#!/usr/bin/env bash
set -euo pipefail

repository_root=$(git rev-parse --show-toplevel)
repository_name=$(basename "$repository_root")

case "$repository_name" in
    Pico-OS)
        release_file="config/os-release.txt"
        release_sources=("$release_file")
        ;;
    PicoC-Compiler)
        release_file="config/compiler-release.txt"
        release_sources=("$release_file" "source/build_version.py")
        ;;
    RETI-Emulator)
        release_file="config/emulator-release.txt"
        release_sources=("$release_file" "include/version.h")
        ;;
    Pico-OS_Presentation)
        release_file="config/presentation-release.txt"
        release_sources=("$release_file")
        ;;
    Pico-OS_Cheatsheet)
        release_file="config/cheatsheet-release.txt"
        release_sources=("$release_file")
        ;;
    *)
        echo "Unsupported repository: $repository_name" >&2
        exit 2
        ;;
esac

cd "$repository_root"
mkdir -p config

if [[ -f "$release_file" ]]; then
    current_version=$(<"$release_file")
else
    current_version="v0.0.0"
fi

if [[ ! "$current_version" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    echo "Invalid version in $release_file: $current_version" >&2
    exit 2
fi

major=${BASH_REMATCH[1]}
minor=${BASH_REMATCH[2]}
patch=${BASH_REMATCH[3]}

printf 'Current version: %s\n\n' "$current_version"
printf '1. Increment patch version: v%s.%s.%s\n' "$major" "$minor" "$((patch + 1))"
printf '2. Increment minor version: v%s.%s.0\n' "$major" "$((minor + 1))"
printf '3. Increment major version: v%s.0.0\n' "$((major + 1))"
printf '4. Use %s again\n' "$current_version"
printf '5. Enter a custom version\n'

while :; do
    read -r -p 'Choose a version [1-5]: ' choice
    case "$choice" in
        1) version="v$major.$minor.$((patch + 1))"; break ;;
        2) version="v$major.$((minor + 1)).0"; break ;;
        3) version="v$((major + 1)).0.0"; break ;;
        4) version="$current_version"; break ;;
        5)
            read -r -p 'Custom version (vX.Y.Z): ' version
            if [[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                break
            fi
            echo 'Version must use the format vX.Y.Z.' >&2
            ;;
        *) echo 'Choose a number from 1 to 5.' >&2 ;;
    esac
done

printf '%s\n' "$version" > "$release_file"
if [[ "$repository_name" == "PicoC-Compiler" ]]; then
    printf 'VERSION = "%s"\n' "$version" > source/build_version.py
elif [[ "$repository_name" == "RETI-Emulator" ]]; then
    printf '#define RETI_EMULATOR_VERSION "%s"\n' "$version" > include/version.h
fi

git add "${release_sources[@]}"
if ! git diff --cached --quiet -- "${release_sources[@]}"; then
    git commit -m "prepare release $version" -- "${release_sources[@]}"
fi

remote=origin
if git remote get-url github >/dev/null 2>&1; then
    remote=github
fi
git push "$remote" HEAD

if git show-ref --verify --quiet "refs/tags/$version"; then
    git tag -d "$version"
fi
if git ls-remote --exit-code --tags "$remote" "refs/tags/$version" >/dev/null 2>&1; then
    git push "$remote" --delete "$version"
fi

git tag -a "$version" -m "Release $version"
git push "$remote" "$version"
